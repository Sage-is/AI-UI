"""Rootstock Phase 0 probe: what SQLite can do inside the shipped image."""
import array, math, operator, os, random, shutil, sqlite3, struct, subprocess, sys, time

D = 384
random.seed(7)
print("python", sys.version.split()[0], "| sqlite", sqlite3.sqlite_version)
c = sqlite3.connect(":memory:")
try:
    c.enable_load_extension(True)
    print("enable_load_extension: ok")
except Exception as e:  # noqa: BLE001
    print("enable_load_extension: FAIL", type(e).__name__, e)
for name, sql in (("fts5", "create virtual table f using fts5(x)"), ("json", "select json('{}')"),
                  ("rtree", "create virtual table r using rtree(id,a,b)"),
                  ("math", "select cos(0.5)")):
    try:
        c.execute(sql)
        print(f"{name}: ok")
    except Exception as e:  # noqa: BLE001
        print(f"{name}: FAIL", e)
opts = [r[0] for r in c.execute("pragma compile_options")]
print("compile_options:", [o for o in opts if any(k in o for k in ("FTS", "JSON", "LOAD", "THREADSAFE", "MATH", "DEFAULT_WAL"))])

def unit(n):
    v = [random.gauss(0, 1) for _ in range(D)]
    s = math.sqrt(sum(x * x for x in v))
    return array.array("f", (x / s for x in v))

q = unit(0)
for n in (5_000, 20_000):
    vecs = [unit(i) for i in range(n)]
    t = time.perf_counter()
    scores = [sum(map(operator.mul, q, v)) for v in vecs]
    top = sorted(range(n), key=scores.__getitem__, reverse=True)[:5]
    print(f"python cosine (pre-normalised) {n}x{D}: {time.perf_counter() - t:.3f}s top={top[:2]}")

uv = shutil.which("uv")
print("uv:", uv)
if uv:
    r = subprocess.run([uv, "pip", "install", "--quiet", "--target", "/tmp/sv", "sqlite-vec"], capture_output=True, text=True)
    print("uv install sqlite-vec rc", r.returncode, (r.stderr or "").strip()[-300:])
    if r.returncode == 0:
        sys.path.insert(0, "/tmp/sv")
        import sqlite_vec  # type: ignore
        sqlite_vec.load(c)
        print("sqlite-vec version:", c.execute("select vec_version()").fetchone()[0])
        c.execute("create table chunk(id integer primary key, embedding blob)")
        n = 50_000
        c.executemany("insert into chunk(embedding) values (?)", ((unit(i).tobytes(),) for i in range(n)))
        qb = q.tobytes()
        for _ in range(3):
            t = time.perf_counter()
            rows = c.execute("select id, vec_distance_cosine(embedding, ?) d from chunk order by d limit 5", (qb,)).fetchall()
            print(f"sqlite-vec scalar cosine {n}x{D}: {time.perf_counter() - t:.3f}s top={rows[0][0]}")
        print("db bytes for 50k x 384 float32:", n * D * 4)
