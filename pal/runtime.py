"""Two runtime lanes and data-only model boundary. Mock is always the default."""
import fcntl
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from pathlib import Path

from .sanitize import sanitize
from .classification import classify, VERSION as CLASSIFIER_VERSION, UNSUPPORTED_REPLY
from .store import Store, StaleResult, EvidenceRejected


@dataclass(frozen=True)
class WorkOrder:
    goal_id: str
    attempt_id: str
    epoch: int
    revision: int
    acceptance_id: str
    specification: str
    context: tuple
    max_bytes: int
    capabilities: tuple = ('local_draft',)


class MockProvider:
    identity = 'mock'

    def __init__(self, task_delay=0):
        if not 0 <= task_delay <= 60:
            raise ValueError('mock delay must be bounded')
        self.task_delay=task_delay
        self._stop=threading.Event()

    def complete(self, prompt):
        if prompt.startswith('DRAFT\n'):
            self._stop.wait(self.task_delay)
            return 'Local draft (mock): ' + prompt.split('\n', 2)[1]
        return 'I have recorded your message. This response uses the mock provider.'

    def stop(self):
        self._stop.set()


class ProviderExecutor:
    """Text generation only; returns a proposal, never an authoritative receipt."""
    def __init__(self, provider):
        self.provider = provider

    def execute(self, order):
        content = self.provider.complete('DRAFT\n' + order.specification + '\nReturn only the requested draft text, without tool invocations or planning transcript.\nRelevant sanitized context: ' + json.dumps(order.context, ensure_ascii=False))
        return {'goal_id': order.goal_id, 'attempt_id': order.attempt_id, 'epoch': order.epoch, 'action': 'local_draft', 'content': content}

    def stop(self):
        self.provider.stop()


class Runtime:
    def __init__(self, path, provider=None, executor=None, fault=None):
        self.started_at=time.time()
        self._closed = threading.Event()
        self._wake = threading.Event()
        self.idle = threading.Event()
        self._reply_lock = threading.Lock()
        self._responses = {}
        self._worker_error = ''
        self._fault = fault or (lambda point: None)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._lockfile = open(str(path) + '.lock', 'a')
        try:
            fcntl.flock(self._lockfile, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._lockfile.close()
            raise RuntimeError('another PAL host owns this canonical store') from None
        try:
            self.store = Store(path)
            self.store.recover()
            self.store.deliver()
        except BaseException:
            self._lockfile.close()
            raise
        self.provider = provider or MockProvider()
        self.executor = executor or ProviderExecutor(self.provider)
        self._conversation = ThreadPoolExecutor(max_workers=2, thread_name_prefix='pal-conversation')
        self._worker = threading.Thread(target=self._work, name='pal-task', daemon=True)
        self._worker.start()
        self._wake.set()

    @staticmethod
    def intent(text):
        return 'draft' if classify(sanitize(text)) == 'draft' else 'conversation'

    def _latest_goal(self):
        goals = self.store.inspect()['goals']
        return goals[-1]['id'] if goals else None

    def submit(self, key, text, goal_id=None, control=None):
        if self._closed.is_set():
            raise RuntimeError('runtime is stopping')
        text = sanitize(text)
        if not isinstance(text, str) or len(text) > 12000:
            raise ValueError('message exceeds input bound')
        original_request={'text':text,'goal_id':goal_id,'control':control}
        lower = text.lower().strip()
        if control is None and lower in ('stop that', 'cancel that', '止めて', '停止して'):
            control = {'action':'cancel'}
            goal_id = self._latest_goal()
        if control is None and lower in ('pause that','一時停止して'):
            control = {'action':'pause'}
            goal_id = self._latest_goal()
        if control is None and lower in ('resume that','再開して'):
            control = {'action':'resume'}
            goal_id = self._latest_goal()
        forget = False
        if control is None and lower in ('forget that','忘れて'):
            prior = [r for r in self.store.inspect()['records'] if r['role']=='user' and r['usable']]
            if prior:
                control = {'source_id':prior[-1]['id']}
                forget = True
        if control is None and lower.startswith('answer:'):
            current_id = self._latest_goal()
            if current_id:
                current = self.store.get_goal(current_id)
                if current['state']=='waiting_input':
                    goal_id = current_id
                    control = {'action':'input','text':text.partition(':')[2].strip(),'question_id':current['question_id'],'epoch':current['epoch']}
        if control is None and lower.startswith('correct that:'):
            goal_id = self._latest_goal()
            if goal_id:
                control = {'action':'correct','text':text.partition(':')[2].strip()}
        classification = None if control is not None else classify(text)
        intent = 'forget' if forget else ('control' if control is not None else ('draft' if classification == 'draft' else 'conversation'))
        result = self.store.ingress(key, text, intent, goal_id, control, request=original_request,
                                  classification=classification, classifier_version=CLASSIFIER_VERSION)
        if lower.startswith('remember ') or '覚えて' in text:
            self.store.note('memory:' + key, text, [result['record_id']])
        if result['goal']:
            self.idle.clear()
            self._wake.set()
        with self._reply_lock:
            response = self._responses.get(key)
            if response is None:
                response = self._conversation.submit(self._respond, key, text, result)
                self._responses[key] = response
        return dict(result, response=response)

    def _respond(self, key, text, ingress):
        stored = self.store.stored_reply(key)
        if stored is not None:
            return stored
        context = self.store.context()
        if ingress['intent']=='forget':
            content = 'Reference stopped. Raw history remains available in Inspect.'
        elif ingress['goal']:
            content = 'Work recorded. Current canonical state: ' + self.store.get_goal(ingress['goal']['id'])['state'] + '.'
        elif ingress.get('classification') == 'unsupported':
            content = UNSUPPORTED_REPLY
        elif any(term in text.lower() for term in ('what happened','previous thing','work status','進捗','どうなった')) and self._latest_goal():
            current=self.store.get_goal(self._latest_goal())
            content='Current work is '+current['state']+'.'+(' Reason: '+current['reason'] if current['reason'] else '')
        else:
            try:
                canonical=[{k:g[k] for k in ('id','state','revision','reason')} for g in self.store.inspect()['goals'][-5:]]
                content = self.provider.complete('CONVERSATION\n' + text + '\nRelevant sanitized context: ' + json.dumps([(r['role'],r['content']) for r in context['records']] + [('note',n['content']) for n in context['notes']], ensure_ascii=False)+'\nCurrent canonical work (overrides old conversation summaries): '+json.dumps(canonical))
            except Exception as error:
                content = 'Conversation provider unavailable: ' + type(error).__name__ + '. Your message remains recorded.'
        try:
            return self.store.record('response:' + key, 'assistant', content, context['manifest'])
        except StaleResult:
            return self.store.record('response:' + key, 'assistant', 'Response withheld because its source references changed.')

    def _apply(self, order, result):
        if not isinstance(result, dict) or result.get('goal_id') != order.goal_id or result.get('attempt_id') != order.attempt_id or result.get('epoch') != order.epoch:
            self.store.fail(order.attempt_id, 'capability_violation')
            return
        token_fields = {'goal_id','attempt_id','epoch'}
        if result.get('action') == 'local_draft' and set(result) == token_fields | {'action','content'} and isinstance(result['content'], str) and len(result['content']) <= order.max_bytes:
            receipt = self.store.write_draft(order.attempt_id, result['content'])
            self.store.complete(order.attempt_id, receipt['id'])
        elif result.get('status') in ('waiting_input','unverified','error') and set(result) == token_fields | {'status','detail'} and isinstance(result['detail'], str) and len(result['detail']) <= 2000:
            if result['status'] == 'waiting_input':
                self.store.waiting(order.attempt_id, result['detail'])
            else:
                self.store.fail(order.attempt_id, result['detail'], result['status'])
        else:
            self.store.fail(order.attempt_id, 'capability_violation')

    def _work(self):
        try:
            self._work_loop()
        except Exception as error:
            self._worker_error='worker_error:'+type(error).__name__
            try:
                for attempt in self.store.inspect()['attempts']:
                    if attempt['status']=='running':
                        self.store.fail(attempt['id'],self._worker_error)
                self.store.record('host-worker-error','assistant',self._worker_error)
            except Exception:
                pass  # Read-only health remains available even if canonical storage fails.
            self.idle.set()

    def health(self):
        return {'pid':os.getpid(),'started_at':self.started_at,'worker_alive':self._worker.is_alive(),'worker_error':self._worker_error,'stopping':self._closed.is_set()}

    def _work_loop(self):
        while not self._closed.is_set():
            self._wake.wait()
            self._wake.clear()
            if self._closed.is_set():
                break
            while not self._closed.is_set():
                context = self.store.context()
                attempt = self.store.claim(context['manifest'])
                if attempt is None:
                    self.store.deliver()
                    self.idle.set()
                    break
                self.idle.clear()
                order = WorkOrder(attempt['goal_id'], attempt['id'], attempt['epoch'], attempt['revision'], attempt['acceptance_id'], attempt['specification'], tuple([(r['role'],r['content']) for r in context['records']] + [('note',n['content']) for n in context['notes']]), attempt['criteria']['max_bytes'])
                try:
                    result = self.executor.execute(order)
                    self._fault('worker.after_executor_before_apply')
                    if self._closed.is_set():
                        break
                    self._apply(order, result)
                except StaleResult:
                    # Store has retained rejection; no current-state mutation.
                    pass
                except EvidenceRejected as error:
                    try:
                        self.store.fail(order.attempt_id, str(error), 'fail')
                    except StaleResult:
                        pass
                except Exception as error:
                    try:
                        self.store.fail(order.attempt_id, 'executor_error:' + type(error).__name__)
                    except StaleResult:
                        pass
                self.store.deliver()
        self.idle.set()

    def close(self):
        if self._closed.is_set():
            return
        self._closed.set()
        self._wake.set()
        stopper = getattr(self.executor, 'stop', None)
        if stopper:
            stopper()
        self.provider.stop()
        self._conversation.shutdown(wait=True)
        self._worker.join(timeout=5)
        if self._worker.is_alive():
            # Keep process lock held: a new host must not recover behind a live worker.
            raise RuntimeError('task worker did not stop; process lock retained')
        fcntl.flock(self._lockfile, fcntl.LOCK_UN)
        self._lockfile.close()
