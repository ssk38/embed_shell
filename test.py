#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from embed_shell import shell, EmbedShell


@shell
def script1(a, b):
    '''#!/bin/bash
       echo hoge
       echo OK!
       echo args=$@
    '''
    pass


class Script1(EmbedShell):
    '''#!/bin/bash
       echo Script1 started
       echo test.py
       echo test2.py
       for ((i=0; i<1024; i++)); do
           echo "************i=$i*************"
           ls -1 /
       done
    '''
    pass


class Script2(EmbedShell):
    '''#!/bin/bash -x
       echo Script2 started
       # read from stdin
       while read line; do
           echo "line=$line"
       done
    '''
    pass


if __name__ == '__main__':
    #import logging
    #logging.basicConfig(level=getattr(logging, 'INFO', None))
    outs, errs, rcs = script1(1, 2)
    print("outs are %s" % outs)
    #print("errs are %s" % errs)
    print("rcs are %s" % rcs)
    scripts = Script1() | Script2()
    print('returned object = %s' % scripts.name)
    outs, errs, rcs = scripts.run()
    print("outs are %s" % outs)
    #print("errs are %s" % errs)
    print("rcs are %s" % rcs)
    sys.exit(0)
    scripts = Script1() | Script2() | EmbedShell('grep test')
    print('returned object = %s' % scripts.name)
    outs, errs, rcs = scripts.run()
    print("outs are %s" % outs)
    #print("errs are %s" % errs)
    print("rcs are %s" % rcs)

    scripts = Script1() | Script2() | EmbedShell('tail -1')
    print('returned object = %s' % scripts.name)
    outs, errs, rcs = scripts.run()
    print("outs are %s" % outs)
    #print("errs are %s" % errs)
    print("rcs are %s" % rcs)

