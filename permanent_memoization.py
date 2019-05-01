'''
Defines decorators used to memoize the results and stdout of function calls to files

Use
@memoize_to_folder("directory_name")
def my_expensive_function(arg1, arg2):
    ...
    return ...

Calling my_expensive_function('1', 5)
will attempt to load the results from a file if it exists.

Calling my_expensive_function('1', 5, __recalculate=True)
will always recalculate and store the results in a file
'''
import pickle
import os
import re
import sys
import textwrap
import glob
import time
try:
    from cStringIO import StringIO
except ModuleNotFoundError:
    from io import StringIO


class MemTee(object):
    ''' Capture stdout to a list as well as printing '''
    def __init__(self):
        # Does nothing if already being tee'd
        self.teeing = False
        self.lines = []
        self._stdout = sys.stdout
        if isinstance(sys.stdout, MemTee):
            return
        self.teeing = True
        sys.stdout = self

    def release(self):
        if self.teeing:
            sys.stdout = self._stdout

    def write(self, data):
        # TODO: This logic is wrong when MemTee's are nested
        self.lines.append(data)
        self._stdout.write(data)

    def flush(self):
        self._stdout.flush()

class Capturing(list):
    ''' Context manager for MemTee '''
    def __enter__(self):
        self.memtee = MemTee()
        return self

    def __exit__(self, *args):
        self.memtee.release()
        self.extend(self.memtee.lines)

def strarg(arg):
    try:
        return re.sub("[^A-Za-z0-9_]", "", arg.__name__)
    except Exception:
        starg = str(arg)
        if starg[0] == '<' and starg[-1] == '>':
            try:
                starg = hash(starg)
            except:
                try:
                    starg = hash(tuple(starg))
                except:
                    pass
                pass
        starg = re.sub("[^A-Za-z0-9_]", "", starg)
        if len(starg) > 100:
            return str(hash(starg))
        return starg

def run_and_capture(fn, fname, capture_stdout, recalculate, args, kwargs,  existing=None):
    with Capturing() as captured:
        rtn = fn(*args, **kwargs)
    output = dict(__rtn = rtn, __args = args, __kwargs = kwargs)
    if capture_stdout:
        if len(captured):
            output['__stdout'] = ' :: ' + ' :: '.join(list(captured))
            output['__stdout'].strip()

    if existing is not None:
        to_write = existing + [output]
    else:
        to_write = [output]

    with open(fname, 'wb') as f:
        try:
            pickle.dump(to_write, f)
        except Exception as e:
            print("Coult not write output to file! {}".format(e))
    return rtn

class BadMemoizationError(Exception):
    pass

def memoize_to_file(fn, dir = '', __capture_stdout=True):
    '''
    A decorator function to memoize the outputs of a function to pickle files
    '''
    if len(dir) > 0:
        try:
            os.makedirs(dir)
        except Exception as e:
            pass

    def delete_memoizations(*args, **kwargs):
        if len(args) == 0 and len(kwargs) == 0:
            print("WARNING: Deleting all memoizations in 5s")
            time.sleep(5)

        fname = os.path.join(dir, fn.__name__)
        for memo_file in glob.glob(fname+'__*.pickle'):
            if len(args) == 0 and len(kwargs) == 0:
                print("Removing file: {}".format(memo_file))
                os.remove(memo_file)
                continue

            with open(memo_file, 'rb') as f:
                try:
                    pkls = pickle.load(f)
                except Exception as e:
                    print("Couldn't read file {}".format(memo_file))
                    continue

                for pkl in pkls:
                    match = True
                    for i, arg in enumerate(args):
                        if i >= len(pkl['__args']) or pkl['__args'][i] != arg:
                            match = False
                            break

                    for kwk, kwv in kwargs.items():
                        if kwk not in pkl['__kwargs'] or kwv != pkl['__kwargs'][kwk]:
                            match = False
                            break

                    if match:
                        print("Removing file: {}".format(memo_file))
                        os.remove(memo_file)
                        break

    def memo_file(*args, **kwargs):
        fname = os.path.join(dir, fn.__name__)
        for argname, arg in zip(fn.__code__.co_varnames, args):
            if argname != '__recalculate':
                fname += '__'+argname + '-' + strarg(arg)

        for argname, arg in kwargs.items():
            if argname != '__recalculate':
                fname += '__'+argname + '-' + strarg(arg)

        for arg in args[len(fn.__code__.co_varnames):]:
            fname += '__arg-' + strarg(arg)

        fname += '.pickle'

        return fname

    def wrapper(*args, **kwargs):
        '''
        The inner function returned by memoize_to_file.
        Serializes arguments for the filename, then writes or reads
        this function's output to that filename.
        Accepts additional __recalculate keywork argument which allows
        it to ignore previous memoization.
        Attempts to call arg.__name__ on arguments, in case they are function objects.
        '''

        recalculate = kwargs.get('__recalculate', False)
        try:
            if '__recalculate' not in fn.__code__.co_varnames:
                del kwargs['__recalculate']
        except KeyError:
            pass

        show_stdout = kwargs.get('show_stdout', __capture_stdout)
        try:
            if 'show_stdout' not in fn.__code__.co_varnames:
                del kwargs['show_stdout']
        except KeyError:
            pass

        fname = memo_file(*args, **kwargs)

        if recalculate:
            return run_and_capture(fn, fname, __capture_stdout, recalculate, args, kwargs)

        if not os.path.exists(fname):
            return run_and_capture(fn, fname, __capture_stdout, recalculate, args, kwargs)

        with open(fname, 'rb') as f:
            print("Loading from {}".format(fname))
            storeds = pickle.load(f)

            for stored in storeds:
                if stored['__kwargs'] != kwargs or stored['__args'] != args:
                    continue
                if '__stdout' in stored and show_stdout:
                    print(":: Cached stdout:\n{}".format(stored['__stdout']))
                if '__rtn' not in stored:
                    raise BadMemoizationError("No return value stored in file!")
                return stored['__rtn']

            return run_and_capture(fn, fname, __capture_stdout, recalculate, args, kwargs, storeds)

    wrapper.memo_file = memo_file
    wrapper.delete_memoizations = delete_memoizations

    return wrapper

def memoize_to_folder(dir, __capture_stdout=True):
    ''' Wrapper function for memoize_to_file so you can decorate a function with:
    @memoize_to_folder(D)
    and all created pickle files will be written to files in the directory D'''
    return lambda fn: memoize_to_file(fn, dir, __capture_stdout)
