from .sandbox import run

ns = {}
print(run("x = 5", ns))
print(ns)
print(run("print(x * 2)", ns))
print(run("1 / 0", ns))
