"""Two runtime lanes and data-only model boundary. Mock is always the default."""
import fcntl
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass
from pathlib import Path

from .sanitize import sanitize
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

    def complete(self, prompt):
        if prompt.startswith('DRAFT\n'):
            return 'Local draft (mock): ' + prompt.split('\n', 2)[1]
        return 'I have recorded your message. This response uses the mock provider.'

    def stop(self):
        pass


class ProviderExecutor:
    """Text generation only; returns a proposal, never an authoritative receipt."""
    def __init__(self, provider):
        self.provider = provider

    def execute(self, order):
        content = self.provider.complete('DRAFT\n' + order.specification + '\nRelevant sanitized context: ' + json.dumps(order.context, ensure_ascii=False))
        return {'goal_id': order.goal_id, 'attempt_id': order.attempt_id, 'epoch': order.epoch, 'action': 'local_draft', 'content': content}

    def stop(self):
        self.provider.stop()


class Runtime:
    def __init__(self, path, provider=None, executor=None, fault=None):
        self._closed = threading.Event()
        self._wake = threading.Event()
        self.idle = threading.Event()
        self._reply_lock = threading.Lock()
        self._responses = {}
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
        lower = text.lower().strip()
        if any(term in lower for term in ('record only', 'not yet', 'later', 'まだ', '記録だけ')):
            return 'conversation'
        if re.match(r'^(?:make|create|write|prepare|please (?:make|create|write|prepare))\b.*\bdraft\b', lower) or lower.startswith('draft ') or ('下書き' in lower and any(term in lower for term in ('作って','作成','お願い'))):
            return 'draft'
        return 'conversation'

    def _latest_goal(self):
        goals = self.store.inspect()['goals']
        return goals[-1]['id'] if goals else None

    def submit(self, key, text, goal_id=None, control=None):
        if self._closed.is_set():
            raise RuntimeError('runtime is stopping')
        text = sanitize(text)
        if not isinstance(text, str) or len(text) > 12000:
            raise ValueError('message exceeds input bound')
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
        intent = 'control' if control is not None else self.intent(text)
        result = self.store.ingress(key, text, intent, goal_id, control)
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
        if ingress['goal']:
            content = 'Work recorded. Current canonical state: ' + self.store.get_goal(ingress['goal']['id'])['state'] + '.'
        else:
            try:
                content = self.provider.complete('CONVERSATION\n' + text + '\nRelevant sanitized context: ' + json.dumps([(r['role'],r['content']) for r in context['records']] + [('note',n['content']) for n in context['notes']], ensure_ascii=False))
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
