"""Builds neofetch.svg: ASCII portrait + profile info + tech stack + live GitHub stats."""
import json, os, subprocess, time, urllib.request
from datetime import date
from html import escape
from PIL import Image, ImageFilter, ImageOps

USER = "itsrajarshi"
CARD_W = 975
W = 59            # characters per info row; every row is stretched to exactly this width
CW = 8.4          # px per info character (textLength pins it, so every font renders the same width)
IX = 450          # info column x
PORTRAIT_RAMP = " .:-=+*#%@"
RAMP = " .'`^\",:;Il!i><~+_-?][}{1)(|/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"

TOK = os.environ.get("GH_TOKEN") or subprocess.check_output(["gh", "auth", "token"], text=True).strip()


def api(path, data=None):
    req = urllib.request.Request(f"https://api.github.com/{path}", data=data, headers={"Authorization": f"bearer {TOK}"})
    return urllib.request.urlopen(req)


def lines_of_code(repos):
    """Sum of lines added/removed by USER across public, non-fork repos (GitHub's contributor stats)."""
    add = dele = 0
    for r in repos:
        for _ in range(5):                       # stats come back 202 while GitHub computes them
            resp = api(f"repos/{USER}/{r}/stats/contributors")
            if resp.status == 200:
                for c in json.load(resp):
                    if c["author"]["login"].lower() == USER:
                        add += sum(w["a"] for w in c["weeks"]); dele += sum(w["d"] for w in c["weeks"])
                break
            time.sleep(3)
    return add, dele


def stats():
    q = f"""query{{user(login:"{USER}"){{createdAt followers{{totalCount}}
      repositoriesContributedTo(first:1,contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,PULL_REQUEST_REVIEW]){{totalCount}}
      repositories(privacy:PUBLIC,ownerAffiliations:OWNER,first:100){{totalCount nodes{{name isFork stargazerCount}}}}}}}}"""
    u = json.load(api("graphql", json.dumps({"query": q}).encode()))["data"]["user"]
    first = int(u["createdAt"][:4])
    yrs = "".join(f'y{y}:contributionsCollection(from:"{y}-01-01T00:00:00Z",to:"{y}-12-31T23:59:59Z"){{totalCommitContributions restrictedContributionsCount}}'
                  for y in range(first, time.gmtime().tm_year + 1))
    c = json.load(api("graphql", json.dumps({"query": f'query{{user(login:"{USER}"){{{yrs}}}}}'}).encode()))["data"]["user"]
    repos = u["repositories"]["nodes"]
    add, dele = lines_of_code([r["name"] for r in repos if not r["isFork"]])
    return {"repos": u["repositories"]["totalCount"], "contributed": u["repositoriesContributedTo"]["totalCount"],
            "stars": sum(r["stargazerCount"] for r in repos), "followers": u["followers"]["totalCount"],
            "commits": sum(v["totalCommitContributions"] + v["restrictedContributionsCount"] for v in c.values()),
            "add": add, "del": dele}


def kv(k, v): return ("kv", k, v)


def uptime(born=date(2005, 2, 16)):
    t = date.today()
    y, m = t.year - born.year, t.month - born.month
    if t.day < born.day: m -= 1
    if m < 0: y, m = y - 1, m + 12
    mo, mn = (t.year, t.month) if t.day >= born.day else ((t.year, t.month - 1) if t.month > 1 else (t.year - 1, 12))
    d = (t - date(mo, mn, born.day)).days
    return f"{y} years, {m} months, {d} days"


INFO = [
    ("title", "rajarshi", "github"),
    ("rule",),
    kv("OS", "Windows 11 (+ Insider), Linux, iOS 27 Beta"),
    kv("Uptime", uptime()),
    kv("Role", "B.Tech CSE Student, Class of 2027"),
    kv("Location", "Visakhapatnam, India"),
    kv("IDE", "Antigravity, VS Code"),
    kv("Cloud", "Google Cloud Arcade Legend"),
    ("blank",),
    kv("Languages.Programming", "Python, JavaScript"),
    kv("Languages.Computer", "HTML, CSS, LaTeX"),
    kv("Languages.Real", "English, Hindi, Bengali, Telugu"),
    ("blank",),
    kv("Hobbies", "Gaming, Custom ROM Modding"),
    kv("Interests", "AI/ML, RAG, NLP, Full-stack"),
    ("blank",),
    ("section", "Contact"),
    kv("Email", "itsmeerajarshi@gmail.com"),
    kv("LinkedIn", "itsrajarshi"),
    kv("YouTube", "@Rajority"),
    kv("Instagram", "itsrajarshi"),
    kv("Discord", "rajxenvy"),
    ("blank",),
    ("section", "GitHub Stats"),
]

STACK = {  # category: [(label, background, text colour)]
    "Languages": [("c", "#00599C", "#fff"), ("c++", "#00599C", "#fff"), ("python", "#3670A0", "#ffdd54"), ("typescript", "#007ACC", "#fff"),
                  ("html5", "#E34F26", "#fff"), ("css3", "#1572B6", "#fff"), ("bash script", "#121011", "#fff"),
                  ("PowerShell", "#5391FE", "#fff"), ("Windows Terminal", "#4D4D4D", "#fff")],
    "Frontend": [("react", "#20232a", "#61DAFB"), ("angular.js", "#E23237", "#fff")],
    "Backend & Servers": [("node.js", "#6DA55F", "#fff"), ("apache", "#D42029", "#fff"), ("apache tomcat", "#F8DC75", "#000")],
    "Databases": [("postgres", "#316192", "#fff"), ("mysql", "#4479A1", "#fff"), ("MongoDB", "#4ea94b", "#fff"),
                  ("sqlite", "#07405e", "#fff"), ("firebase", "#a08021", "#ffcd34"), ("Supabase", "#3ECF8E", "#fff")],
    "ML / Data Science": [("TensorFlow", "#FF6F00", "#fff"), ("PyTorch", "#EE4C2C", "#fff"), ("numpy", "#013243", "#fff"),
                          ("pandas", "#150458", "#fff"), ("Matplotlib", "#ffffff", "#000"), ("Plotly", "#3F4F75", "#fff")],
    "Cloud & DevOps": [("GoogleCloud", "#4285F4", "#fff"), ("git", "#F05033", "#fff"), ("github", "#121011", "#fff"),
                       ("gitlab", "#181717", "#fff"), ("gitlab CI", "#181717", "#fff"), ("selenium", "#43B02A", "#fff")],
    "Design & Tools": [("Canva", "#00C4CC", "#fff"), ("adobe", "#FF0000", "#fff"), ("Adobe Lightroom", "#31A8FF", "#fff")],
}


def ascii_art(first, last, x=25, cw=400 / 120):
    """Text portrait from assets/portrait.png (pre-toned, masked): brighter pixel = denser character, background blank.
    Rows are spread so the first/last baselines sit on the info panel's first/last baselines."""
    im = Image.open("assets/portrait.png")
    cols, rows = im.size
    lh = (last - first) / (rows - 1)
    y = first - lh
    g, m = im.getchannel(0).load(), im.getchannel(1).load()
    out = []
    for j in range(rows):
        row = "".join(" " if m[i, j] < 128 else PORTRAIT_RAMP[min(9, int((0.15 + 0.85 * (g[i, j] / 255)) * 10))] for i in range(cols))
        out.append(f'<text class="art" xml:space="preserve" x="{x}" y="{y + (j + 1) * lh:.1f}" textLength="{cols * cw:.1f}" lengthAdjust="spacing">{escape(row)}</text>')
    return "\n".join(out)


def info_rows(s):
    rows = INFO + [
        ("pair", "Repos", f"{s['repos']} {{Contributed: {s['contributed']}}}", "Stars", f"{s['stars']:,}"),
        ("pair", "Commits", f"{s['commits']:,}", "Followers", f"{s['followers']:,}"),
        ("loc", "Lines of Code on GitHub", f"{s['add'] - s['del']:,}", f"{s['add']:,}++", f"{s['del']:,}--"),
    ]
    out, iy = [], 40
    for i, row in enumerate(rows):
        kind, full = row[0], True
        if kind == "title":
            t, full = f'<tspan class="u">{row[1]}</tspan>@<tspan class="u">{row[2]}</tspan>', False
        elif kind == "rule":
            t = f'<tspan class="d">{"-" * W}</tspan>'
        elif kind == "section":
            t = f'- {row[1]} <tspan class="d">{"-" * (W - len(row[1]) - 3)}</tspan>'
        elif kind == "kv":                         # every branch below produces exactly W characters
            dots = "." * (W - len(row[1]) - len(row[2]) - 3)
            t = f'<tspan class="k">{escape(row[1])}</tspan>:<tspan class="d"> {dots} </tspan><tspan class="v">{escape(row[2])}</tspan>'
        elif kind == "pair":                       # "Repos: .... 8 {Contributed: 3} | Stars: .... 0"
            k1, v1, k2, v2 = row[1:]
            d1, d2 = "." * (35 - len(k1) - len(v1)), "." * (15 - len(k2) - len(v2))
            t = (f'<tspan class="k">{k1}</tspan>:<tspan class="d"> {d1} </tspan><tspan class="v">{escape(v1)}</tspan> | '
                 f'<tspan class="k">{k2}</tspan>:<tspan class="d"> {d2} </tspan><tspan class="v">{v2}</tspan>')
        elif kind == "loc":
            k, total, a, d = row[1:]
            dots = "." * (W - len(k) - len(total) - len(a) - len(d) - 8)
            t = (f'<tspan class="k">{k}</tspan>:<tspan class="d"> {dots} </tspan><tspan class="v">{total}</tspan> '
                 f'(<tspan class="add">{a}</tspan>, <tspan class="del">{d}</tspan>)')
        else:
            continue
        tl = f' textLength="{W * CW:.1f}" lengthAdjust="spacing"' if full else ""
        out.append(f'<text xml:space="preserve" x="{IX}" y="{iy + i * 20}"{tl}>{t}</text>')
    return "\n".join(out), iy + len(rows) * 20


def stack_block(y0):
    """Shields-style pills drawn as SVG (external badge images are blocked inside a GitHub-rendered SVG)."""
    span = CARD_W - 50
    out = [f'<text x="25" y="{y0}" textLength="{span}" lengthAdjust="spacing">- Tech Stack <tspan class="d">{"-" * (int(span / CW) - 13)}</tspan></text>']
    y = y0 + 22
    for cat, pills in STACK.items():
        out.append(f'<text class="cat" x="25" y="{y + 14}">{escape(cat)}</text>')
        x = 190
        for label, bg, fg in pills:
            w = len(label) * 7 + 18
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="20" rx="4" fill="{bg}" stroke="#30363d"/>'
                       f'<text class="pill" x="{x + w / 2}" y="{y + 14}" text-anchor="middle" style="fill:{fg}">{escape(label)}</text>')
            x += w + 6
        y += 28
    return "\n".join(out), y - y0 + 10


def build():
    info, info_bottom = info_rows(stats())
    top = info_bottom - 10
    stack, stack_h = stack_block(top + 30)
    h = top + 30 + stack_h + 15
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{CARD_W}" height="{h}" viewBox="0 0 {CARD_W} {h}">
<style>
text{{font-family:ConsolasFallback,Consolas,"DejaVu Sans Mono","Courier New",monospace;font-size:15px;fill:#c9d1d9;white-space:pre}}
.art{{font-size:5.6px;fill:#c9d1d9}}
.k,.u{{fill:#ffa657;font-weight:bold}} .v{{fill:#a5d6ff}} .add{{fill:#3fb950}} .del{{fill:#f85149}} .d{{fill:#484f58}}
.cat{{font-size:12px;fill:#8b949e}} .pill{{font-size:12px;font-weight:bold}}
</style>
<rect width="{CARD_W}" height="{h}" rx="15" fill="#161b22"/>
{ascii_art(40, info_bottom - 20)}
{info}
{stack}
</svg>
'''


if __name__ == "__main__":
    open("neofetch.svg", "w", encoding="utf-8").write(build())
