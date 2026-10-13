from swarmtrace import tracer

for _ in range(3):
    tracer.message("a", "b", {"retry": True})
