"""Private exchange CLI. No service discovery, authority, native acceptance or custody.

Linux container tools must be independently pinned; Windows mode bits are NOT a
DACL. Host creates inherited private DACL before invoking. Size/time limits are
NOT OS quotas. Trees must be stopped and helper-owned. No secure erase claim.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys


def sibling(name):
    spec = importlib.util.spec_from_file_location('_exchange_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

native = sibling('multistore_native')
archive = sibling('multistore_archive')
require = native.require


def initialize(root):
    root = Path(os.path.abspath(root))
    native.checked_directory(root.parent)
    root.mkdir(mode=0o700)  # Claim only after exclusive mkdir; never remove collision.
    for name in ('exports','keys','work','reports','sql','inbox'):
        (root/name).mkdir(mode=0o700)
    for name in archive.COMPONENTS:
        (root/'exports'/name).mkdir(mode=0o700)
    native.write_new(root/'keys/n8n.key', secrets.token_hex(32).encode())
    native.write_new(root/'exports/key-references/references.json', native.encode_json({
        'schema':1,'n8n':'ephemeral-exercise-only','age':'ephemeral-exercise-only',
        'operationalCustodyProven':False}))
    return {'verified':True,'operationalCustodyProven':False}


def tree_inventory(root):
    root = native.checked_directory(root)
    entries, total = [], 0
    def walk(directory):
        nonlocal total
        with os.scandir(directory) as iterator:
            for entry in iterator:
                require(len(entries) < 4096)
                p=Path(entry.path); name=p.relative_to(root).as_posix();archive._name(name)
                if entry.is_dir(follow_symlinks=False):
                    archive._node(p,True);entries.append({'path':name,'directory':True});walk(p)
                else:
                    info=archive._node(p);total+=info.st_size;require(total<=archive.MAX_TOTAL)
                    entries.append({'path':name,'bytes':info.st_size,'sha256':archive._file_digest(p)})
    walk(root)
    return sorted(entries,key=lambda x:x['path'])


def transfer_tree(source, destination):
    source, destination=Path(source).absolute(),Path(destination).absolute()
    require(not destination.is_relative_to(source) and not source.is_relative_to(destination))
    before=tree_inventory(source);native.checked_directory(destination.parent)
    destination.mkdir(mode=0o700)
    try:
        for item in before:
            target=destination/item['path']
            if item.get('directory'): target.mkdir(mode=0o700)
            else:
                with (source/item['path']).open('rb') as inp,target.open('xb') as out:
                    os.chmod(target,0o600);shutil.copyfileobj(inp,out,65536)
        require(before==tree_inventory(source)==tree_inventory(destination))
    except BaseException:
        shutil.rmtree(destination);raise
    return {'verified':True,'files':sum(not x.get('directory',False) for x in before)}


def restore_tree(source, destination):
    """Fill an EXISTING empty directory (e.g. a mounted volume root); never replace it.

    Unlike transfer_tree the destination is not created. Anything not empty, hidden
    entries included, is rejected before any write. On failure only entries this call
    created are removed; the destination directory itself is left in place.
    """
    # abspath normalises '..'; Path.absolute() would let a path that merely looks external slip through.
    source, destination=Path(os.path.abspath(source)),Path(os.path.abspath(destination))
    require(not destination.is_relative_to(source) and not source.is_relative_to(destination))
    before=tree_inventory(source)
    destination=native.checked_directory(destination)
    with os.scandir(destination) as iterator:
        require(next(iterator,None) is None)
    created=[]
    try:
        for item in before:
            target=destination/item['path']
            if item.get('directory'):
                target.mkdir(mode=0o700);created.append(target)
            else:
                with (source/item['path']).open('rb') as inp,target.open('xb') as out:
                    created.append(target);os.chmod(target,0o600);shutil.copyfileobj(inp,out,65536)
        require(before==tree_inventory(source)==tree_inventory(destination))
    except BaseException:
        for target in sorted(created,key=lambda x:len(x.parts),reverse=True):
            if target.is_dir() and not target.is_symlink(): shutil.rmtree(target,ignore_errors=True)
            else: target.unlink(missing_ok=True)
        raise
    return {'verified':True,'files':sum(not x.get('directory',False) for x in before)}


def copy_file(source,destination,expected):
    source,destination=Path(source).absolute(),Path(destination).absolute()
    native.checked_directory(destination.parent)
    require(archive._file_digest(source)==expected)
    owned=False
    try:
        with source.open('rb') as inp,destination.open('xb') as out:
            owned=True;os.chmod(destination,0o600);shutil.copyfileobj(inp,out,65536)
        require(archive._file_digest(source)==expected==archive._file_digest(destination))
    except BaseException:
        if owned: destination.unlink()
        raise
    return {'verified':True,'sha256':expected}


def keygen(root, executable, expected):
    root=native.checked_directory(root);tool=Path(executable)
    require(tool.is_absolute() and archive._file_digest(tool)==expected)
    # File destinations exclusive; keygen itself uses fixed argv and env.
    for stem in ('identity','wrong-identity'):
        target=root/(stem+'.txt')
        with target.open('xb') as out:
            os.chmod(target,0o600)
            r=subprocess.run([str(tool)],stdout=out,stderr=subprocess.DEVNULL,env={},timeout=15,check=False)
        require(r.returncode==0);archive._identities(target)
    require(not (archive._identities(root/'identity.txt') & archive._identities(root/'wrong-identity.txt')))
    target=root/'recipient.txt'
    with target.open('xb') as out:
        os.chmod(target,0o600)
        r=subprocess.run([str(tool),'-y',str(root/'identity.txt')],stdout=out,stderr=subprocess.DEVNULL,env={},timeout=15)
    require(r.returncode==0 and target.stat().st_size<=1024 and archive._file_digest(tool)==expected)
    return {'verified':True,'operationalCustodyProven':False}


def call_helper(helper,args,stdout_file):
    require(helper in ('multistore_native','multistore_speckle','multistore_n8n','multistore_archive'))
    # Helper sanitizes stdout. Persist report privately, not through host logging.
    target=Path(stdout_file).absolute();native.checked_directory(target.parent)
    with target.open('xb') as out:
        os.chmod(target,0o600)
        result=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name(helper+'.py')),*args],
            stdout=out,stderr=subprocess.DEVNULL,env=dict(os.environ),timeout=600)
    require(result.returncode==0 and target.stat().st_size<=1048576)
    value=native.json_document(native.read_file(target,1048576))
    require(type(value) is dict)
    return value


def equal_files(left,right):
    a=native.json_document(native.read_file(Path(left),4194304));b=native.json_document(native.read_file(Path(right),4194304))
    require(native.semantic_equal(a,b));return {'verified':True}


def main(argv=None):
    try:
        parser=native.Parser(add_help=False,allow_abbrev=False)
        sub=parser.add_subparsers(dest='mode',required=True,parser_class=native.Parser)
        p=sub.add_parser('init',add_help=False);p.add_argument('--root',required=True)
        for name in ('tree','restore-tree','copy','equal'):
            p=sub.add_parser(name,add_help=False)
            p.add_argument('--source',required=True);p.add_argument('--destination',required=True)
            if name=='copy':p.add_argument('--sha256',required=True)
        p=sub.add_parser('keygen',add_help=False)
        for k in ('root','tool','sha256'):p.add_argument('--'+k,required=True)
        p=sub.add_parser('call',add_help=False)
        p.add_argument('--helper',required=True);p.add_argument('--stdout-file',required=True);p.add_argument('args',nargs=argparse.REMAINDER)
        p=sub.add_parser('hash',add_help=False);p.add_argument('--source',required=True)
        args=parser.parse_args(argv)
        if args.mode=='init': result=initialize(args.root)
        elif args.mode=='tree':result=transfer_tree(args.source,args.destination)
        elif args.mode=='restore-tree':result=restore_tree(args.source,args.destination)
        elif args.mode=='copy':result=copy_file(args.source,args.destination,args.sha256)
        elif args.mode=='equal':result=equal_files(args.source,args.destination)
        elif args.mode=='hash':result={'verified':True,'sha256':archive._file_digest(Path(args.source))}
        elif args.mode=='keygen':result=keygen(args.root,args.tool,args.sha256)
        else:result=call_helper(args.helper,args.args[1:] if args.args[:1]==['--'] else args.args,args.stdout_file)
        print(json.dumps(result,sort_keys=True));return 0
    except Exception:
        print('{"verified":false,"error":"EXCHANGE_REJECTED"}');return 1

if __name__=='__main__':raise SystemExit(main())
