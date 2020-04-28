import asyncio

from aiomirai import MessageChain
from aioredis import create_redis_pool
from quart import abort, request

from bot import api, app, conf

try:
    import ujson as json
except ImportError:
    import json

def _get_header(header):
    try:
        return request.headers[header]
    except:
        abort(400, f'Missing header \'{header}\' :(')

@app.route('/github', ['POST'])
async def _():
    event_type = _get_header('X-Github-Event')
    content_type = _get_header('content-type')
    if content_type == 'application/x-www-form-urlencoded':
        formdata = (await request.form).to_dict(flat=True)
        data = json.loads(formdata['payload'])
    elif content_type == 'application/json':
        data = await request.get_json()
    else:
        abort(415, f'Content type \"{content_type}\" NOT supported :(')

    if data is None:
        abort(400, 'Where is your data :(')

    if event_type in EVENT_DESCRIPTIONS.keys():
        res = EVENT_DESCRIPTIONS[event_type].format(**data)
    elif event_type == 'star':
        if not data['action'] == 'created':
            return '', 204
        try:
            redis = await create_redis_pool(conf['redis'], encoding='utf-8')
            if await redis.sismember(
                    'github',
                    '{sender[login]}:{repository[full_name]}'.format(**data)
                ):
                return '', 204
            res = '{sender[login]} stared {repository[full_name]}' \
                '(total {repository[stargazers_count]} stargazers)'.format(**data)
            await redis.sadd(
                'github',
                '{sender[login]}:{repository[full_name]}'.format(**data)
            )
        finally:
            redis.close()
            await redis.wait_closed()
    elif event_type == 'push':
        res = '{pusher[name]} pushed to {repository[full_name]}:{ref}'.format(**data)
        for commit in data['commits']:
            det = []
            if len(commit['added']):
                det.append('{}+'.format(len(commit['added'])))
            if len(commit['removed']):
                det.append('{}-'.format(len(commit['removed'])))
            if len(commit['modified']):
                det.append('{}M'.format(len(commit['modified'])))
            res += '\n{} {} ({})' \
                .format(commit['id'][:6], commit['message'].replace('\n', ' '), ''.join(det))
    else:
        return '', 204
    if res and conf['github'][data['repository']['full_name']]:
        coros = []
        for group in conf['github'][data['repository']['full_name']]:
            coros.append(api.send_group_message(target=group, message_chain=MessageChain(res)))
        await asyncio.gather(*coros)
        return 'Pushed to {} group(s).'.format(len(conf['github'][data['repository']['full_name']]))


EVENT_DESCRIPTIONS = {
    'commit_comment':
    '{comment[user][login]} commented on {comment[commit_id]} in {repository[full_name]}',
    'create':
    '{sender[login]} created {ref_type} ({ref}) in {repository[full_name]}',
    'delete':
    '{sender[login]} deleted {ref_type} ({ref}) in {repository[full_name]}',
    'deployment':
    '{sender[login]} deployed {deployment[ref]} to {deployment[environment]} in {repository[full_name]}',
    'deployment_status':
    'deployment of {deployement[ref]} to {deployment[environment]} {deployment_status[state]} in {repository[full_name]}',
    'fork':
    '{forkee[owner][login]} forked {forkee[name]}',
    'gollum':
    '{sender[login]} edited wiki pages in {repository[full_name]}',
    'issue_comment':
    '{sender[login]} commented on issue #{issue[number]} in {repository[full_name]}',
    'issues':
    '{sender[login]} {action} issue #{issue[number]} in {repository[full_name]}',
    'member':
    '{sender[login]} {action} member {member[login]} in {repository[full_name]}',
    'membership':
    '{sender[login]} {action} member {member[login]} to team {team[name]} in {repository[full_name]}',
    'page_build':
    '{sender[login]} built pages in {repository[full_name]}',
    'ping':
    'ping from {sender[login]}',
    'public':
    '{sender[login]} publicized {repository[full_name]}',
    'pull_request':
    '{sender[login]} {action} pull #{pull_request[number]} in {repository[full_name]}',
    'pull_request_review':
    '{sender[login]} {action} {review[state]} review on pull #{pull_request[number]} in {repository[full_name]}',
    'pull_request_review_comment':
    '{comment[user][login]} {action} comment on pull #{pull_request[number]} in {repository[full_name]}',
    'release':
    '{release[author][login]} {action} {release[tag_name]} in {repository[full_name]}',
    'repository':
    '{sender[login]} {action} repository {repository[full_name]}',
    'status':
    '{sender[login]} set {sha} status to {state} in {repository[full_name]}',
    'team_add':
    '{sender[login]} added repository {repository[full_name]} to team {team[name]}',
}
