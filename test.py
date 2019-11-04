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
       ls -1 /
       echo test.py
       echo test2.py
       exit 1
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
    # import logging
    # logging.basicConfig(level=getattr(logging, 'INFO', None))
    outs, errs = script1(1, 2)
    print("outs is %s" % outs)
    print("errs is %s" % errs)
    scripts = Script1() | Script2() | EmbedShell('grep test')
    print('returned object = %s' % scripts.name)
    outs, errs = scripts.run()
    print("outs is %s" % outs)
    print("errs is %s" % errs)
