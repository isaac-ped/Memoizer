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
        if isinstance(sys.stdout, MemTee):
            return
        self.teeing = True
        self._stdout = sys.stdout
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
        if len(starg) > 50:
            return str(hash(starg))
        return starg

def run_and_capture(fn, fname, __capture_stdout, *args, **kwargs):
    with Capturing() as captured:
        rtn = fn(*args, **kwargs)
    output = dict(__rtn = rtn)
    if __capture_stdout:
        if len(captured):
            output['__stdout'] = ' :: ' + ' :: '.join(list(captured))
            output['__stdout'].strip()
    with open(fname, 'wb') as f:
        try:
            pickle.dump(output, f)
        except Exception as e:
            print("Coult not write output to file! {}".format(e))
    return rtn

def memoize_to_file(fn, dir = '', __capture_stdout=True):
    '''
    A decorator function to memoize the outputs of a function to pickle files
    '''
    if len(dir) > 0:
        try:
            os.makedirs(dir)
        except Exception as e:
            pass


    def wrapper(*args, **kwargs):
        '''
        The inner function returned by memoize_to_file.
        Serializes arguments for the filename, then writes or reads
        this function's output to that filename.
        Accepts additional __recalculate keywork argument which allows
        it to ignore previous memoization.
        Attempts to call arg.__name__ on arguments, in case they are function objects.
        '''

        __recalculate = kwargs.get('__recalculate', False)
        try:
            del kwargs['__recalculate']
        except KeyError:
            pass

        fname = os.path.join(dir, fn.__name__)
        for argname, arg in zip(fn.__code__.co_varnames, args):
            fname += '__'+argname + '-' + strarg(arg)

        for argname, arg in kwargs.items():
            fname += '__'+argname + '-' + strarg(arg)

        if len(fname) > 255:
            fname = hash(fname)

        fname += '.pickle'

        if __recalculate:
            return run_and_capture(fn, fname, __capture_stdout, *args, **kwargs)

        try:
            with open(fname, 'rb') as f:
                print("Loading from {}".format(fname))
                rtn = pickle.load(f)
                if '__stdout' in rtn and len(rtn['__stdout']) and __capture_stdout:
                    print(":: Cached stdout:\n{}".format(rtn['__stdout']))
                if '__rtn' in rtn:
                    return rtn['__rtn']
                else:
                    return rtn
        except Exception as e:
            return run_and_capture(fn, fname, __capture_stdout, *args, **kwargs)

    return wrapper

def memoize_to_folder(dir, __capture_stdout=True):
    ''' Wrapper function for memoize_to_file so you can decorate a function with:
    @memoize_to_folder(D)
    and all created pickle files will be written to files in the directory D'''
    return lambda fn: memoize_to_file(fn, dir, __capture_stdout)
