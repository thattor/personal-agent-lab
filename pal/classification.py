"""Conservative, finite local-document request grammar; no state or model calls."""
import re
import unicodedata

VERSION = 'local-draft-1'
UNSUPPORTED_REPLY = ('I cannot send or perform external actions. No work was started. '
                     '/ 送信などの外部操作には対応していません。作業は開始していません。')


def _skeleton(text):
    text = unicodedata.normalize('NFKC', text).casefold()
    text = ''.join(c for c in text if unicodedata.category(c) != 'Cf')
    text = text.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    pairs = {'"': '"', "'": "'", '「': '」', '『': '』'}
    closing = {'」', '』'}
    output, end = [], None
    for i, c in enumerate(text):
        # Apostrophes in contractions are not quoted instruction delimiters.
        if c == "'" and i and i + 1 < len(text) and text[i-1].isalnum() and text[i+1].isalnum():
            if not end:
                output.append(c)
            continue
        if end:
            if c == end:
                end = None
                output.append(' payload ')
            elif c in pairs or c in closing:
                return None  # Nested/ambiguous quoting never authorizes work.
        elif c in pairs:
            end = pairs[c]
        elif c in closing:
            return None
        else:
            output.append(c)
    return None if end else re.sub(r'\s+', ' ', ''.join(output)).strip()


def classify(text):
    if not isinstance(text, str) or len(text) > 12000:
        return 'conversation'
    s = _skeleton(text)
    if not s:
        return 'conversation'
    s = s.replace('たたき台', '下書き')
    # Decline an instruction's reporting/meta/conditional frame, not its payload.
    if re.search(r'^(?:record only|not yet|not now|if\b|suppose\b)|\b(?:he|she|they) (?:said|asked|told)|\b(?:what does|would making|are you able)\b|記録だけ|記録のみ|覚えて|もし|仮に|と言(?:った|いました|われ)|と彼が言|頼まれた|書いてあった|聞かれた|って何|作れますか|作るつもり|作成する予定|作りたい', s):
        return 'conversation'
    if re.search(r"actually,? (?:do not|don't)|やっぱり(?:やめ|作らない)|今はまだ.*(?:実行しない|作らない)", s):
        return 'conversation'
    if re.match(r'^(?:あとで|後で|明日|来月になったら)[、, ]', s):
        return 'conversation'
    # Split sibling clauses; never scan quoted payload for effect verbs.
    clauses = re.split(r'[。.!！?？;；、,]|\b(?:and|but|then)\s+(?=(?:please\s+)?(?:send|email|mail|forward|post|publish|share|submit|upload|deliver|make|write|book|delete|summarize|translate|run|execute|do\b))', s)
    draft = False
    unknown_action = False
    for clause in clauses:
        c = clause.strip(' ,?？')
        if not c:
            continue
        # First-person future action is information, not delegated action.
        if re.match(r"^(?:i will|i'll|i am going to|i'm going to)\b", c):
            continue
        # Remove only explicit prohibitions of external actions in this clause.
        verbs = r'(?:send(?:ing)?|email(?:ing)?|mail(?:ing)?|forward(?:ing)?|post(?:ing)?|publish(?:ing)?|share|sharing|submit(?:ting)?|upload(?:ing)?|deliver(?:ing)?)'
        effect = re.sub(r"\b(?:do not|don't|without|not) " + verbs + r'(?:\s+(?:or|and)\s+' + verbs + r')*(?:\s+(?:it|this|them))?', ' ', c)
        effect = re.sub(r'\b(?:send|sending) (?:is )?not requested\b', ' ', effect)
        effect = re.sub(r'(?:送信|送ら|送って|転送|投稿|共有|提出)(?:は|を)?(?:しないで|ないで|しません|しない|不要|禁止)', ' ', effect)
        if re.search(r"^(?:(?:please|just|could you|can you|would you)\s+)*(?:send|email|mail|forward|reply to|post|publish|share|submit|upload|deliver|cc)\b|\b(?:send|email|mail|forward|post|publish|share|submit|upload|deliver) (?:it|this|them|the (?:draft|email|invitation))\b|(?:送信|転送|投稿|共有|提出|返信|メール)(?:だけ|は|を)?して|送って|送信をお願い", effect):
            return 'unsupported'
        # Request deferral attaches to drafting, not an invitation's date.
        deferred = re.search(r'^(?:あとで|後で|明日|来月になったら).*下書き|\b(?:draft|make|write|create|prepare)\b.*(?<!for )\b(?:later|tomorrow)(?:,? not now|,? not yet|$)|(?:下書き.*(?:あとで|後で).*(?:作って|作成)|下書き.*(?:作って|作成).*(?:あとで|後で))', c)
        negated = re.search(r"^(?:do not|don't|please do not|no need to)\b|(?:下書き.*(?:作らない|作らなくて|作成しない))", c)
        if deferred or negated:
            continue
        en = re.match(r"^(?:(?:please|can you|could you|would you|i need you to|i'd like you to)\s+)?(?:(?:make|create|write|prepare|put together)\b.*\bdraft\b|draft\s+(?:a|an|the|it|an? invitation|invitations|an? invite))", c)
        mood = r'(?:ください|ほしい(?:です)?|もらえますか|もらえませんか|くれますか|くれる)?$'
        jp = re.search(r'下書き.{0,32}(?:作って|作成して|として書いて|書いて|用意して|にして)' + mood + r'|下書き.{0,32}お願い(?:します|できますか)?$|下書き(?:を)?(?:して|してください)(?:もらえますか)?$', c)
        if en or jp:
            draft = True
        elif re.match(r'^(?:book|delete|summarize|translate|run|execute)\b', c):
            unknown_action = True
    if draft and unknown_action:
        return 'unsupported'
    return 'draft' if draft else 'conversation'
