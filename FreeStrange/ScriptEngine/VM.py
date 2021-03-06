"""
Virtual Machine
"""
import io
import sqlite3
import sys
from collections import deque
from . import keyword_list, wait_list, start_end_list


class Stack(deque):
    push = deque.append

    def top(self):
        return self[-1]

    def __hash__(self):
        return True


class VirtualMachine:
    def __init__(self, code, strange=None):
        self.data_stack = Stack()
        self.return_stack = Stack()
        self.instruction_pointer = 0
        self.code = code
        self.base = self.__dict__
        self.strange = strange
        self.dispatch_map = {
            # Base
            "%": self.mod,
            "*": self.mul,
            "+": self.plus,
            "-": self.minus,
            "/": self.div,
            "==": self.eq,
            "cast_int": self.cast_int,
            "cast_str": self.cast_str,
            "drop": self.drop,
            "dup": self.dup,
            "exit": self.exit,
            "if": self.if_stmt,
            "jmp": self.jmp,
            "over": self.over,
            "print": self.print,
            "println": self.println,
            "read": self.read,
            "stack": self.dump_stack,
            "swap": self.swap,
        }
        if type(strange) is io.TextIOWrapper:
            self.strange = strange
            self.dispatch_map.update({
                # Data
                "=": self.value,
                "show": self.show,
                "save": self.save,
                "use": self.use
            })
        elif type(strange) is sqlite3.Cursor:
            self.sqlite = strange

    def pop(self):
        return self.data_stack.pop()

    def push(self, value):
        self.data_stack.push(value)

    def top(self):
        return self.data_stack.top()

    def run(self):
        while self.instruction_pointer < len(self.code):
            opcode = self.code[self.instruction_pointer]
            self.instruction_pointer += 1
            self.dispatch(opcode)

    def dispatch(self, op):
        if op in self.dispatch_map:
            self.dispatch_map[op]()
        elif isinstance(op, int):
            self.push(op)  # push numbers on stack
        elif isinstance(op, str):
            self.push(op)  # push quoted strings on stack
        else:
            raise RuntimeError("Unknown opcode: '%s'" % op)

    # OPERATIONS FOLLOW:

    def plus(self):
        self.push(self.pop() + self.pop())

    @staticmethod
    def exit():
        sys.exit(0)

    def minus(self):
        last = self.pop()
        self.push(self.pop() - last)

    def mul(self):
        self.push(self.pop() * self.pop())

    def div(self):
        last = self.pop()
        self.push(self.pop() / last)

    def mod(self):
        last = self.pop()
        self.push(self.pop() % last)

    def dup(self):
        self.push(self.top())

    def over(self):
        b = self.pop()
        a = self.pop()
        self.push(a)
        self.push(b)
        self.push(a)

    def drop(self):
        self.pop()

    def swap(self):
        b = self.pop()
        a = self.pop()
        self.push(b)
        self.push(a)

    def print(self):
        sys.stdout.write(str(self.pop()))
        sys.stdout.flush()

    def println(self):
        sys.stdout.write("%s\n" % self.pop())
        sys.stdout.flush()

    def read(self):
        self.push(input())

    def cast_int(self):
        self.push(int(self.pop()))

    def cast_str(self):
        self.push(str(self.pop()))

    def eq(self):
        self.push(self.pop() == self.pop())

    def if_stmt(self):
        false_clause = self.pop()
        true_clause = self.pop()
        test = self.pop()
        self.push(true_clause if test else false_clause)

    def jmp(self):
        address = self.pop()
        if isinstance(address, int) and 0 <= address < len(self.code):
            self.instruction_pointer = address
        else:
            raise RuntimeError("JMP address must be a valid integer.")

    def dump_stack(self):
        print("Data stack (top first):")

        for v in reversed(self.data_stack):
            print(" - type %s, value '%s'" % (type(v), v))

    # data function
    def value(self):
        v2 = self.pop()
        v1 = self.pop()
        if type(v2) == int or bool:
            exec('global ' + v1)
            exec(v1 + '=' + str(v2) + '')
        elif type(v2) == str:
            exec('global ' + v1)
            exec(v1 + '="' + v2 + '"')
        else:
            raise TypeError('type not support')

    def change(self):
        v2 = self.pop()
        v1 = self.pop()
        exec('global ' + v1)
        exec(v1 + '=' + v2)

    def show(self):
        var = self.pop()
        exec('global ' + var)
        print(eval(var))
        sys.stdout.write(str(exec(var)))

    def save(self):
        self.strange.write(str(self.pop()))

    def use(self):
        pass


class Preprocessor:
    def __init__(self, code):
        self.stack = []
        self.out = []
        wait = []
        end = []
        for i in code:
            if len(wait) != 0:
                self.out += self.stack
                self.out.append(i)
                self.out += wait
                wait.pop()
                self.stack = []
            elif (i in keyword_list) and (i in start_end_list):
                end.append(i)
            elif (i in keyword_list) and (i in wait_list):
                wait.append(i)
            elif (i in keyword_list) and (i not in wait_list):
                self.out.append(i)
            else:
                self.stack.append(i)
        self.out += end
