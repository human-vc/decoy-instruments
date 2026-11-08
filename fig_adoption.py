import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

rows = [
    ("DeepSeek V4.1 Flash", 0.008, 0.000, 0.025, 0.000, 0.000, 0.000),
    ("Gemini 3.8 Flash", 0.000, 0.000, 0.000, 0.000, 0.000, 0.000),
    ("Gemini 4 Argon", 0.000, 0.000, 0.000, 0.000, 0.000, 0.000),
    ("Gemma 4 31B", 0.667, 0.492, 0.825, 0.583, 0.408, 0.750),
    ("GPT-4o mini", 0.692, 0.550, 0.825, 0.000, 0.000, 0.000),
    ("GPT-5 mini", 0.158, 0.058, 0.267, 0.125, 0.042, 0.225),
    ("GPT-6.1 Sol", 0.000, 0.000, 0.000, 0.000, 0.000, 0.000),
    ("Claude Haiku 4.5", 0.733, 0.558, 0.883, 0.425, 0.275, 0.583),
    ("Claude Haiku 5.5", 0.017, 0.000, 0.042, 0.008, 0.000, 0.025),
    ("Claude Opus 5.5", 0.000, 0.000, 0.000, 0.000, 0.000, 0.000),
    ("Qwen 3.8 27B", 0.000, 0.000, 0.000, 0.000, 0.000, 0.000),
    ("Claude Sonnet 5.5", 0.000, 0.000, 0.000, 0.000, 0.000, 0.000),
]
rows.sort(key=lambda r: (r[1], r[4]))

plt.rcParams.update({"font.size": 8, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(6.2, 2.2))
ys = range(len(rows))
off = 0.17
for y, (name, a, alo, ahi, f, flo, fhi) in zip(ys, rows):
    ax.plot([alo, ahi], [y + off] * 2, color="#1f4e79", lw=1.4)
    ax.plot(a, y + off, "o", color="#1f4e79", ms=4.5)
    ax.plot([flo, fhi], [y - off] * 2, color="#c0504d", lw=1.4)
    ax.plot(f, y - off, "s", color="#c0504d", ms=4)
ax.axvline(0.10, color="0.55", ls=":", lw=0.9)
ax.set_yticks(list(ys))
ax.set_yticklabels([r[0] for r in rows])
ax.set_xlim(-0.02, 1.0)
ax.set_ylim(-0.6, len(rows) - 0.4)
ax.set_xlabel("Share of responses that use the ruled-out variable as the instrument")
ax.plot([], [], "o-", color="#1f4e79", ms=4.5, label="Adoption (any use)")
ax.plot([], [], "s-", color="#c0504d", ms=4, label="Informed adoption (use while naming the problem)")
ax.legend(loc="lower right", frameon=False, fontsize=7)
fig.tight_layout()
fig.savefig("fig_adoption.pdf")
