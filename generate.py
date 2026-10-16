"""Builds neofetch.svg: HUD-framed portrait + profile info + live GitHub stats."""
import base64, io, json, os, subprocess, time, urllib.request
from datetime import date
from html import escape
from PIL import Image, ImageOps

USER = "itsrajarshi"
W = 58  # width of the dotted info column


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


def photo_block(x=25, y=30, n=400, c="#39d0ff"):
    """Photo with a cyan duotone, scanlines, HUD brackets and a moving scan beam."""
    im = Image.open("assets/avatar.png").convert("RGB").resize((n, n), Image.LANCZOS)
    duo = ImageOps.colorize(ImageOps.autocontrast(ImageOps.grayscale(im)), "#031018", "#bff6ff", mid="#0a6f8f")
    im = Image.blend(im, duo, 0.72)  # keep some real colour so it still looks like you
    buf = io.BytesIO(); im.save(buf, "JPEG", quality=85)
    uri = base64.b64encode(buf.getvalue()).decode()
    br = lambda d: f'<path d="{d}" fill="none" stroke="{c}" stroke-width="2.5"/>'
    return f'''<defs>
<clipPath id="c"><rect x="{x}" y="{y}" width="{n}" height="{n}" rx="10"/></clipPath>
<pattern id="sl" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1.5" fill="#000" opacity=".28"/></pattern>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c}" stop-opacity="0"/><stop offset="1" stop-color="{c}" stop-opacity=".45"/></linearGradient>
</defs>
<g clip-path="url(#c)">
<image x="{x}" y="{y}" width="{n}" height="{n}" href="data:image/jpeg;base64,{uri}"/>
<rect x="{x}" y="{y}" width="{n}" height="32" fill="#031018" opacity=".7"/><rect x="{x}" y="{y+n-30}" width="{n}" height="30" fill="#031018" opacity=".7"/>
<rect x="{x}" y="{y}" width="{n}" height="{n}" fill="url(#sl)"/>
<rect class="beam" x="{x}" y="{y}" width="{n}" height="46" fill="url(#beam)"/>
</g>
{br(f"M{x+4} {y+28}V{y+4}H{x+28}")}{br(f"M{x+n-28} {y+4}H{x+n-4}V{y+28}")}{br(f"M{x+4} {y+n-28}V{y+n-4}H{x+28}")}{br(f"M{x+n-28} {y+n-4}H{x+n-4}V{y+n-28}")}
<text class="hud" x="{x+16}" y="{y+22}">// SUBJECT_01</text>
<text class="hud" x="{x+n-16}" y="{y+22}" text-anchor="end">CSE &#183; 2027</text>
<text class="hud" x="{x+16}" y="{y+n-14}"><tspan class="blink">&#9679;</tspan> ONLINE</text>
<text class="hud" x="{x+n-16}" y="{y+n-14}" text-anchor="end">AI/ML &#183; FULL-STACK</text>'''


def build():
    s = stats()
    info = INFO + [
        ("pair", "Repos", f"{s['repos']} {{Contributed: {s['contributed']}}}", "Stars", f"{s['stars']:,}"),
        ("pair", "Commits", f"{s['commits']:,}", "Followers", f"{s['followers']:,}"),
        ("loc", "Lines of Code on GitHub", f"{s['add'] - s['del']:,}", f"{s['add']:,}++", f"{s['del']:,}--"),
    ]
    ix, iy = 450, 40
    out = [photo_block()]
    for i, row in enumerate(info):
        y, kind = iy + i * 20, row[0]
        if kind == "title":
            t = f'<tspan class="u">{row[1]}</tspan>@<tspan class="u">{row[2]}</tspan>'
        elif kind == "rule":
            t = f'<tspan class="d">{"-" * W}</tspan>'
        elif kind == "section":
            t = f'- {row[1]} <tspan class="d">{"-" * (W - len(row[1]) - 3)}</tspan>'
        elif kind == "kv":
            dots = "." * max(2, W - len(row[1]) - len(row[2]) - 2)
            t = f'<tspan class="k">{escape(row[1])}</tspan>:<tspan class="d"> {dots} </tspan><tspan class="v">{escape(row[2])}</tspan>'
        elif kind == "pair":                       # "Repos: .... 8 {Contributed: 3} | Stars: .... 0"
            k1, v1, k2, v2 = row[1:]
            d1 = "." * max(2, 35 - len(k1) - len(v1) - 2); d2 = "." * max(2, 17 - len(k2) - len(v2) - 2)
            t = (f'<tspan class="k">{k1}</tspan>:<tspan class="d"> {d1} </tspan><tspan class="v">{escape(v1)}</tspan> | '
                 f'<tspan class="k">{k2}</tspan>:<tspan class="d"> {d2} </tspan><tspan class="v">{v2}</tspan>')
        elif kind == "loc":
            k, total, a, d = row[1:]
            dots = "." * max(2, W - len(k) - len(total) - len(a) - len(d) - 9)
            t = (f'<tspan class="k">{k}</tspan>:<tspan class="d"> {dots} </tspan><tspan class="v">{total}</tspan> '
                 f'(<tspan class="add">{a}</tspan>, <tspan class="del">{d}</tspan>)')
        else:
            continue
        out.append(f'<text x="{ix}" y="{y}" xml:space="preserve">{t}</text>')
    h = max(30 + 400, iy + len(info) * 20) + 20
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1010" height="{h}" viewBox="0 0 1010 {h}">
<style>
text{{font-family:Consolas,"Courier New",monospace;font-size:15px;fill:#c9d1d9}}
.k,.u{{fill:#ffa657;font-weight:bold}} .v{{fill:#a5d6ff}} .add{{fill:#3fb950}} .del{{fill:#f85149}} .d{{fill:#484f58}}
.hud{{font-size:11px;fill:#39d0ff;letter-spacing:1px}}
.blink{{animation:b 1.4s infinite}} .beam{{animation:s 3.2s linear infinite}}
@keyframes b{{50%{{opacity:.2}}}} @keyframes s{{from{{transform:translateY(-46px)}}to{{transform:translateY(400px)}}}}
</style>
<rect width="1010" height="{h}" rx="12" fill="#0d1117" stroke="#30363d"/>
{chr(10).join(out)}
</svg>
'''


if __name__ == "__main__":
    open("neofetch.svg", "w", encoding="utf-8").write(build())
