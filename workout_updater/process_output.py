# SHAMEFULLY VIBE-CODED / AI-GENERATED; REVIEW AND TEST BEFORE USE.
"""Stream subprocess pipes without a shell, preserving stdout/stderr and timeout.

Engine supplies a per-line callback for private diagnostics and safe classification.
A selector drains both pipes; bounded in-memory tails retain command parse results.
Raw private output is independent of the bounded browser-safe console.
"""
import os
import selectors
import subprocess
import time


def stream_run(args,*,env,input=None,timeout=120,on_line=None):
    """Run fixed argv, deliver complete lines promptly, kill/reap on timeout/error."""
    process=subprocess.Popen(args,stdin=subprocess.PIPE if input is not None else subprocess.DEVNULL,
                             stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=env)
    selector=selectors.DefaultSelector();buffers={};tails={'stdout':bytearray(),'stderr':bytearray()}
    deadline=time.monotonic()+timeout
    try:
        if input is not None:
            process.stdin.write(input.encode() if isinstance(input,str) else input);process.stdin.close()
        for name,pipe in (('stdout',process.stdout),('stderr',process.stderr)):
            os.set_blocking(pipe.fileno(),False);selector.register(pipe,selectors.EVENT_READ,name);buffers[name]=bytearray()
        while selector.get_map():
            remaining=deadline-time.monotonic()
            if remaining<=0:raise subprocess.TimeoutExpired(args,timeout)
            for key,_ in selector.select(min(.2,remaining)):
                chunk=os.read(key.fileobj.fileno(),8192);name=key.data
                if not chunk:
                    selector.unregister(key.fileobj)
                    if buffers[name] and on_line:on_line(buffers[name].decode('utf-8','replace'))
                    buffers[name].clear();continue
                tails[name].extend(chunk)
                if len(tails[name])>2097152:del tails[name][:-2097152]
                buffers[name].extend(chunk)
                # Treat progress carriage returns as line boundaries. Bound a
                # single unterminated line so hostile output cannot exhaust RAM.
                buffers[name][:]=buffers[name].replace(b'\r',b'\n')
                while b'\n' in buffers[name]:
                    line,_,rest=buffers[name].partition(b'\n');buffers[name]=bytearray(rest)
                    if on_line:on_line(line.decode('utf-8','replace'))
                if len(buffers[name])>16384:
                    if on_line:on_line(buffers[name].decode('utf-8','replace'))
                    buffers[name].clear()
        result=process.wait(timeout=max(.001,deadline-time.monotonic()))
        return subprocess.CompletedProcess(args,result,tails['stdout'].decode('utf-8','replace'),tails['stderr'].decode('utf-8','replace'))
    except BaseException:
        process.kill();process.wait();raise
    finally:
        selector.close();process.stdout.close();process.stderr.close()
