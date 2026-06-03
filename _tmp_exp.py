import sqlite3, os, tempfile

# --- Case 2: db path is a directory -> connect fails, makedirs on parent succeeds
d = tempfile.mkdtemp()
chemin = os.path.join(d, "data", "fakenews.db")
os.makedirs(chemin)  # create a DIRECTORY at the db path
# now mimic __init__:
dossier = os.path.dirname(chemin)
os.makedirs(dossier, exist_ok=True)  # parent already exists -> ok
try:
    sqlite3.connect(chemin)
    print("CASE2: NO ERROR (bad)")
except sqlite3.Error as e:
    print("CASE2 ok:", type(e).__name__, e)

# --- Case 3: parent is a file -> makedirs raises
d2 = tempfile.mkdtemp()
parent_as_file = os.path.join(d2, "data")
with open(parent_as_file, "w") as f:
    f.write("x")
chemin2 = os.path.join(parent_as_file, "fakenews.db")
dossier2 = os.path.dirname(chemin2)  # == parent_as_file (a file)
try:
    os.makedirs(dossier2, exist_ok=True)
    print("CASE3: NO ERROR (bad)")
except OSError as e:
    print("CASE3 ok:", type(e).__name__, e)

# --- Case 1: wrapper connection whose cursor.execute fails on first call
class _CurseurKO:
    def __init__(self, vrai):
        self._vrai = vrai
    def execute(self, *a, **k):
        raise sqlite3.OperationalError("disk I/O error simulee")
    def __getattr__(self, n):
        return getattr(self._vrai, n)

class _ConnKO:
    def __init__(self, vraie):
        self._vraie = vraie
        self.rollback_appele = False
    def cursor(self, *a, **k):
        return _CurseurKO(self._vraie.cursor(*a, **k))
    def rollback(self):
        self.rollback_appele = True
        return self._vraie.rollback()
    def __getattr__(self, n):
        return getattr(self._vraie, n)

d3 = tempfile.mkdtemp()
chemin3 = os.path.join(d3, "data", "fakenews.db")
os.makedirs(os.path.dirname(chemin3), exist_ok=True)
real = sqlite3.connect(chemin3)
wrap = _ConnKO(real)
cur = wrap.cursor()
try:
    cur.execute("CREATE TABLE IF NOT EXISTS analyses (id INTEGER)")
    print("CASE1: NO ERROR (bad)")
except sqlite3.Error as e:
    wrap.rollback()
    print("CASE1 ok:", type(e).__name__, e, "rollback_appele=", wrap.rollback_appele)
# inspect with a fresh real connection
insp = sqlite3.connect(chemin3)
c = insp.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
print("CASE1 tables:", [r[0] for r in c.fetchall()])
