import json, os, pathlib, subprocess, tempfile

launcher = pathlib.Path(__file__).resolve().parents[1] / 'agent-worktree'
fixture_directory = tempfile.TemporaryDirectory(prefix='launcher-test-')
root = pathlib.Path(fixture_directory.name).resolve()
repo = root / 'source repo'
repo.mkdir()
def run(args, cwd=repo, env=None):
    return subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
def git(*args):
    result = run(['git', *args])
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()
git('init', '-q')
git('config', 'user.email', 'fixture@example.invalid')
git('config', 'user.name', 'Launcher Fixture')
(repo / 'tracked').write_text('original')
(repo / '.codex').mkdir()
(repo / '.codex/setup.sh').write_text('''#!/usr/bin/env bash
set -eu
test "$PWD" = "$AGENT_WORKTREE_PATH"
test -f "$AGENT_SOURCE_PATH/tracked"
printf '%s' "$AGENT_TASK_NAME" > setup-ran
exit "${FIXTURE_SETUP_EXIT:-0}"
''')
git('add', '.')
git('commit', '-qm', 'fixture with setup')
base = git('rev-parse', 'HEAD')
bin_dir = root / 'bin'
bin_dir.mkdir()
agent = bin_dir / 'codex'
agent.write_text('''#!/usr/bin/env python3
import json, os, pathlib, sys
pathlib.Path(os.environ['FIXTURE_RESULT']).write_text(json.dumps({'cwd':os.getcwd(),'args':sys.argv[1:],'source':os.environ['AGENT_SOURCE_PATH'],'task':os.environ['AGENT_TASK_NAME']}))
sys.exit(int(os.environ.get('FIXTURE_AGENT_EXIT','0')))
''')
agent.chmod(0o755)
env = dict(os.environ, PATH=str(bin_dir)+os.pathsep+os.environ['PATH'], AGENT_WORKTREES_DIR=str(root/'checkouts'))
checks = []
def launch(name, args=(), extra=None, cwd=repo, expected=0):
    receipt=root/(name+'.json')
    config=dict(env, FIXTURE_RESULT=str(receipt))
    config.update(extra or {})
    result=run([str(launcher),name,*args],cwd,config)
    assert result.returncode==expected, (name,result.returncode,result.stdout,result.stderr)
    checks.append(name)
    return json.loads(receipt.read_text()) if receipt.exists() else None, result

(repo/'tracked').write_text('uncommitted')
data,_=launch('default-agent')
checkout=pathlib.Path(data['cwd'])
assert (checkout/'tracked').read_text()=='original'
assert (checkout/'setup-ran').read_text()=='default-agent'
assert (repo/'tracked').read_text()=='uncommitted'
data,_=launch('arguments',[str(agent),'two words','$(not-executed)','--flag'])
assert data['args']==['two words','$(not-executed)','--flag']
data,_=launch('relative-agent',[os.path.relpath(agent,repo)])
assert pathlib.Path(data['cwd']).exists()
data,_=launch('relative-root',extra={'AGENT_WORKTREES_DIR':'../relative checkouts'})
assert pathlib.Path(data['cwd']).parent.parent==root/'relative checkouts'
data,result=launch('setup-failure',extra={'FIXTURE_SETUP_EXIT':'23'},expected=23)
assert data is None and 'worktree retained' in result.stderr
launch('agent-failure',extra={'FIXTURE_AGENT_EXIT':'17'},expected=17)
first,_=launch('repeat')
second,_=launch('repeat')
assert first['cwd']!=second['cwd']
launch('missing-agent',['nonexistent-agent-fixture'],expected=1)
before=git('worktree','list','--porcelain')
launch('invalid-ref',extra={'AGENT_BASE_REF':'no-such-fixture-ref'},expected=128)
assert git('worktree','list','--porcelain')==before
result=run([str(launcher),'../bad'],env=env)
assert result.returncode==1
checks.append('invalid-name')
result=run([str(launcher)],env=env)
assert result.returncode!=0
checks.append('missing-name')
(repo/'subdir').mkdir()
launch('from-subdirectory',cwd=repo/'subdir')
git('checkout','--','tracked')
git('rm','.codex/setup.sh')
git('commit','-qm','fixture without setup')
data,_=launch('without-setup')
assert not (pathlib.Path(data['cwd'])/'setup-ran').exists()
data,_=launch('explicit-base',extra={'AGENT_BASE_REF':base})
assert (pathlib.Path(data['cwd'])/'setup-ran').exists()
assert git('status','--porcelain')==''
print(json.dumps({'passed':len(checks),'cases':checks,'fixtures':str(root)},indent=2))
