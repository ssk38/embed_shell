#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import re
import signal
import subprocess
import tempfile
from functools import reduce

def shell(function):
    print(f'shell deco called')
    print(function.__doc__)
    eshell = EmbedShell()
    eshell.set_script(function.__doc__)
    eshell.name = function.__name__

    def runshell(*args):
        print(f'runshell {args}')
        return eshell.run(*args)

    return runshell


class EmbedShell:
    '''Run __doc__ as script and returns output. Supports pipe by | operand.'''

    def __init__(self, *args, name=None):
        print(f"__init__ called")
        self.script_string = None
        self.args = []
        self.pipe_children = [self]
        self.rc = None
        self.pipe_status = None

        if self.__class__.__name__ != 'EmbedShell':
            logging.info(f"__init__ called from inherited class {self.__class__.__name__}")
            self.set_script(self.__doc__)
            self.set_args(*args)
            if name:
                self.name = name
            else:
                self.name = self.__class__.__name__
        elif args:
            logging.info(f"__init__ called as {args}")
            if len(args) > 1:
                raise ValueError('EmbedShell accepts only one argument of string literal')
            self.set_script('#!/bin/sh\n ' + args[0])
            self.name = args[0].split()[0]

    def _remove_base_indent(self, script):
        lines = script.split('\n')
        if len(lines) <= 1:
            return script

        # Search the min indent line
        get_indent = re.compile(r'(\s+)')
        m = get_indent.match(lines[0])
        if m:
            # first line has indent, take it into account
            topline_has_indent = True
            min_indent = len(m.group(0))
        else:
            topline_has_indent = False
            min_indent = 0xffff  # just large enough number
        for line in lines[1:]:
            m = get_indent.match(line[0])
            if not m:
                raise ValueError(f'Invalid indent at {line}')
            indent = len(m.group(0))
            if indent < min_indent:
                min_indent = indent
        # strip indent
        if topline_has_indent:
            lines[0] = lines[0][min_indent:]
        for i in range(1, len(lines)):
            lines[i] = lines[i][min_indent:]
        return '\n'.join(lines)

    def set_script(self, doc):
        self.script_string = self._remove_base_indent(doc)

    def set_args(self, *args):
        if args:
            self.args = list(map(str, list(args)))

    def __ror__(self, other_eshell):
        if not isinstance(other_eshell, EmbedShell):
            raise ValueError("EmbedShell pipe accepts only string or EmbedShell")

        other_eshell.pipe_children.append(self)
        return other_eshell

    def popen(self, *args, stdout=None, stdin=None, stderr=None, cwd=None, **kwargs):
        fd, self.script_file = tempfile.mkstemp(prefix=f"{self.name}_")
        logging.info(f'writing script to {self.script_file}')
        with open(self.script_file, 'w') as fp:
            fp.write(self.script_string)
        os.chmod(self.script_file, 0o500)
        if args:
            self.args = list(map(str, list(args)))

        logging.info(f'Running {self.script_file} {self.args}')
        return subprocess.Popen([self.script_file] + self.args,
                                encoding='utf-8',
                                cwd=cwd,
                                stdout=stdout,
                                stdin=stdin,
                                stderr=stderr,
                                **kwargs)

    def _popenall(self, *args,
                  stdin=subprocess.PIPE,
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
                  **kwargs):
        self.processes = []
        prev_in = stdout
        for child in reversed(self.pipe_children):
            if self.pipe_children[0] == child:
                _stdin = stdin
            else:
                _stdin = subprocess.PIPE

            p = child.popen(stdout=prev_in,
                            stdin=_stdin,
                            stderr=stderr,
                            **kwargs)
            setattr(p, "embedshell_name", child.name)
            logging.info(f"Popening({child.name})")
            self.processes.insert(0, p)
            prev_in = p.stdin
        
        logging.info([(p.embedshell_name, p.args) for p in self.processes])
        return self.processes[0].stdin, self.processes[-1].stdout

    def run(self, *args, **kwargs):
        if args:
            if len(self.pipe_children) == 1:
                self.set_args(*args)
            else:
                raise ValueError("run(*args) not allowed for pipe context. Use constructre to pass args")
        self._popenall(*args, **kwargs)
        pfirst = self.processes[0]
        plast = self.processes[-1]

        outs = ""
        errs = ""
        # TODO: Output must smaller than buffer, otherwise we hangs here
        #       because no one eats stdout PIPE of last process.
        logging.info(f'{pfirst.embedshell_name} finished')
        if pfirst == plast:
            outs, errs = plast.communicate(timeout=1)
        else:
            finished_process = list(map(lambda a: a is None, self.processes))

            while True:
                for i in range(len(self.processes)):
                    if finished_process[i]:
                        continue
                    p = self.processes[i]
                    logging.info(f'polling {p.embedshell_name}')
                    #if p.poll() is None:
                    #    # This process is alive, kill SIGPIPE
                    #    logging.info(f'kill {p.embedshell_name}')
                    #    p.send_signal(signal.SIGPIPE)

                    try:
                        _outs, _errs = p.communicate(timeout=1)
                        logging.info(f"{p.embedshell_name} finished. outs={_outs}, errs={_errs}")
                        outs = _outs
                        errs += _errs
                    except:
                        import traceback
                        traceback.print_exc()

                    if p.poll() is not None:
                        p.wait(timeout=1)
                        '''
                        pipes are used by forked children, so we
                        don't need it.
                        But we MUST close it because keeping it open
                        prevents the termination behaviour
                        (SIGPIPE).
                        If we keep it open, when the one side
                        of process finished, the other side
                        hungs keeping wait for next data
                        without recieving SIGPIPE.
                        '''
                        if p.stdout:
                            p.stdout.close()
                        if p.stderr:
                            p.stderr.close()
                        if p.stdin:
                            p.stdin.close()
                        finished_process[i] = True
                    logging.info(f'{p.embedshell_name} finished')

                if reduce(lambda a,b: a and b, [p.poll() is not None for p in self.processes], True):
                    # all process finished.
                    break
                print([p.poll() is not None for p in self.processes])
        logging.info(outs)
        logging.info(errs)

        self.rc = plast.returncode
        self.pipe_status = [p.returncode for p in self.processes]
        return outs, errs, self.pipe_status
