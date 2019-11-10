#!/usr/bin/python

import os, sys
import subprocess

def fail(msg):
    print msg
    exit(1)

sha1 = sys.argv[1]

if len(sha1) != 40:
    fail('usage: %s <SHA1-sum>' % (sys.argv[0],))

def gitroot():
    git = os.path.join(os.getcwd(), '.git')
    if not os.path.isdir(git):
        fail('cannot find .git/')
    return git

obj = os.path.join(gitroot(), 'objects', sha1[:2], sha1[2:])

if not os.path.isfile(obj):
    fail('cannot find %s' % obj)

def validate(sha1):
    process = subprocess.Popen(['git', 'cat-file', '-t', sha1], stdout=subprocess.PIPE)
    out, err = process.communicate()
    result = subprocess.call(['git', 'cat-file', out.strip(), sha1])
    return result == 0

if validate(sha1):
    print 'object looks ok!'
    exit(0)

with open(obj, 'rb') as f:
    contents = f.read()
assert len(contents) == 12288

# create a backup
bkp = obj
while os.path.exists(bkp):
    bkp += "~"
os.rename(obj, bkp)

def lengths(contents):
    '''Yield guesses of the correct length of an object'''
    totlen = len(contents)
    pos = totlen - 1
    candidates = []
    while pos > 0:
        if contents[pos] == '\0' and contents[pos - 1] != '\0':
            candidates.append(pos)
        pos -= 1

    endpoints = set(candidates)
    endpoints.add(totlen)
    candidates.append(0)

    while candidates:
        cand = candidates.pop(0)
        yield cand
        if cand + 1 not in endpoints:
            candidates.append(cand + 1)

for length in lengths(contents):
    print 'trying length', length
    sys.stdout.flush()
    with open(obj, 'wb') as f:
        f.write(contents[:length])
    if validate(sha1):
        print 'repaired!'
        exit(0)
    sys.stdout.flush()

print 'Giving up!'
exit(1)
