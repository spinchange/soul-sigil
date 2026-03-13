#!/usr/bin/env python3
"""
Soul Sigil Generator
Reads machine hardware, generates a unique visual sigil + bytebeat WAV.

Usage:
  python soul_sigil.py [--color1 #RRGGBB] [--color2 #RRGGBB]
                       [--duration 300] [--no-hostname] [--out ./output]
"""

import argparse
import hashlib
import math
import os
import platform
import struct
import uuid


# ── Hardware Collection ──────────────────────────────────────────────────────

def collect_hardware(include_hostname=True):
    hw = {}
    collected = []

    try:
        mac = uuid.getnode()
        hw['mac'] = format(mac, 'x')
        collected.append(f"  MAC address:   {hw['mac']}")
    except Exception:
        pass

    try:
        hw['cpu'] = platform.processor() or platform.machine()
        collected.append(f"  CPU:           {hw['cpu']}")
    except Exception:
        pass

    try:
        hw['arch'] = platform.machine()
        collected.append(f"  Architecture:  {hw['arch']}")
    except Exception:
        pass

    try:
        hw['os'] = f"{platform.system()} {platform.release()}"
        collected.append(f"  OS:            {hw['os']}")
    except Exception:
        pass

    try:
        hw['cores'] = str(os.cpu_count() or 0)
        collected.append(f"  CPU cores:     {hw['cores']}")
    except Exception:
        pass

    if include_hostname:
        try:
            hw['hostname'] = platform.node()
            collected.append(f"  Hostname:      {hw['hostname']}")
        except Exception:
            pass

    print("Hardware fingerprint collected:")
    for line in collected:
        print(line)
    print()
    return hw


def hash_hardware(hw_dict):
    fingerprint = '|'.join(f"{k}={v}" for k, v in sorted(hw_dict.items()))
    return hashlib.sha256(fingerprint.encode()).hexdigest().upper()


# ── Parameter Derivation ─────────────────────────────────────────────────────

def derive_params(hash_str, color1=None, color2=None):
    seed1 = int(hash_str[0:8], 16)
    seed2 = int(hash_str[8:16], 16)
    seed3 = int(hash_str[16:24], 16)

    c1 = color1 or f"#{hash_str[0:6]}"
    c2 = color2 or f"#{hash_str[6:12]}"

    v1 = (seed1 % 10) + 5    # 5–14
    v2 = (seed2 % 10) + 2    # 2–11
    v3 = (seed3 % 5)  + 12   # 12–16  (slow mask — controls era length)
    v4 = (seed1 % 4)  + 6    # 6–9

    return {
        'hash':    hash_str,
        'color1':  c1,
        'color2':  c2,
        'seed1':   seed1,
        'v1': v1, 'v2': v2, 'v3': v3, 'v4': v4,
        'formula': f"t*(t>>{v1}|t>>{v2})&(t>>{v3})&(t>>{v4})",
    }


# ── Sigil Glyph (unique rune drawn from hash) ────────────────────────────────

def _lcg(s):
    return (s * 1664525 + 1013904223) & 0xFFFFFFFF


def generate_sigil_lines(seed_int, n=9):
    """Connect hash-derived points on a circle to form a unique glyph."""
    pts = []
    for i in range(n):
        angle = 2 * math.pi * i / n - math.pi / 2
        pts.append((100 + 65 * math.cos(angle), 100 + 65 * math.sin(angle)))

    s = seed_int
    connections = set()
    cur = 0
    for _ in range(n * 3):
        s = _lcg(s)
        nxt = s % n
        if nxt != cur:
            connections.add((min(cur, nxt), max(cur, nxt)))
        cur = nxt

    parts = []
    for (i, j) in sorted(connections):
        x1, y1 = pts[i]
        x2, y2 = pts[j]
        parts.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    for x, y in pts:
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5"/>')

    return '\n            '.join(parts)


# ── HTML Generation ──────────────────────────────────────────────────────────

def generate_html(params):
    c1        = params['color1']
    c2        = params['color2']
    hash_str  = params['hash']
    formula   = params['formula']
    v1, v2, v3, v4 = params['v1'], params['v2'], params['v3'], params['v4']
    glyph     = generate_sigil_lines(params['seed1'])

    # f-string: {{ }} = literal brace in output
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Soul Sigil</title>
    <style>
        :root {{ --c1: {c1}; --c2: {c2}; }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            background: radial-gradient(circle at center, #1a1a1f 0%, #050507 100%);
            color: #fff;
            font-family: 'Cascadia Code', 'Courier New', monospace;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            overflow: hidden;
        }}
        canvas {{ position: fixed; top: 0; left: 0; z-index: -1; opacity: 0.25; }}
        .container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 2rem;
        }}
        .sigil-wrap {{
            width: 360px;
            height: 360px;
            position: relative;
            filter: drop-shadow(0 0 28px color-mix(in srgb, var(--c1) 50%, transparent));
        }}
        .amoeba {{
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, var(--c1), var(--c2));
            border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%;
            animation: morph 20s infinite alternate cubic-bezier(0.45,0.05,0.55,0.95);
            opacity: 0.85;
        }}
        @keyframes morph {{
            0%   {{ border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; transform: rotate(0deg)   scale(1);    }}
            50%  {{ border-radius: 30% 60% 70% 40% / 50% 60% 30% 60%; transform: rotate(180deg) scale(1.08); }}
            100% {{ border-radius: 60% 40% 30% 70% / 60% 30% 70% 40%; transform: rotate(360deg) scale(1);    }}
        }}
        .glyph {{
            position: absolute;
            inset: 20px;
            mix-blend-mode: screen;
        }}
        .glyph line, .glyph circle {{
            stroke: rgba(255,255,255,0.65);
            stroke-width: 1.2;
            fill: none;
        }}
        .glyph circle {{ fill: rgba(255,255,255,0.45); stroke: none; }}
        .meta {{
            text-align: center;
            max-width: 520px;
            padding: 0 1rem;
        }}
        .label {{
            font-size: 0.65rem;
            text-transform: uppercase;
            color: #555;
            letter-spacing: 0.12em;
            margin-bottom: 0.35rem;
        }}
        .hash {{
            font-size: 0.7rem;
            color: var(--c1);
            word-break: break-all;
            margin-bottom: 1.2rem;
            font-weight: bold;
            line-height: 1.5;
        }}
        .formula-box {{
            background: rgba(0,0,0,0.4);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 6px;
            padding: 0.75rem 1.2rem;
            color: #88ff88;
            font-size: 0.9rem;
            margin-bottom: 1.2rem;
        }}
        #play-btn {{
            background: none;
            border: 1px solid var(--c1);
            color: var(--c1);
            padding: 0.5rem 2rem;
            cursor: pointer;
            border-radius: 4px;
            font-family: inherit;
            font-size: 0.85rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            transition: all 0.2s;
        }}
        #play-btn:hover {{
            background: var(--c1);
            color: #000;
            box-shadow: 0 0 18px var(--c1);
        }}
    </style>
</head>
<body>
<canvas id="stars"></canvas>
<div class="container">
    <div class="sigil-wrap">
        <div class="amoeba"></div>
        <svg class="glyph" viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg">
            {glyph}
        </svg>
    </div>
    <div class="meta">
        <div class="label">Hardware Soul Hash</div>
        <div class="hash">{hash_str}</div>
        <div class="label">Bytebeat Heartbeat</div>
        <div class="formula-box">{formula}</div>
        <button id="play-btn">Initialize Pulse</button>
    </div>
</div>
<script>
    // Starfield
    const canvas = document.getElementById('stars');
    const ctx = canvas.getContext('2d');
    let w, h;
    function resize() {{ w = canvas.width = innerWidth; h = canvas.height = innerHeight; }}
    window.onresize = resize; resize();
    const stars = Array(180).fill(0).map(() => ({{
        x: Math.random()*w, y: Math.random()*h,
        size: Math.random()*1.8, speed: Math.random()*0.4+0.1
    }}));
    (function tick() {{
        ctx.clearRect(0, 0, w, h);
        ctx.fillStyle = '#fff';
        stars.forEach(s => {{
            ctx.beginPath(); ctx.arc(s.x, s.y, s.size, 0, Math.PI*2); ctx.fill();
            s.y -= s.speed; if (s.y < 0) s.y = h;
        }});
        requestAnimationFrame(tick);
    }})();

    // Bytebeat
    const v1={v1}, v2={v2}, v3={v3}, v4={v4};
    let audioCtx, t = 0;
    const btn = document.getElementById('play-btn');
    btn.onclick = () => {{
        if (!audioCtx) {{
            audioCtx = new (window.AudioContext || window.webkitAudioContext)({{ sampleRate: 8000 }});
            const gain = audioCtx.createGain(); gain.gain.value = 0.5;
            const node = audioCtx.createScriptProcessor(4096, 1, 1);
            node.onaudioprocess = e => {{
                const out = e.outputBuffer.getChannelData(0);
                for (let i = 0; i < out.length; i++) {{
                    out[i] = (((t * (t>>v1 | t>>v2) & (t>>v3) & (t>>v4)) & 255) / 127.5) - 1;
                    t++;
                }}
            }};
            node.connect(gain); gain.connect(audioCtx.destination);
            btn.textContent = 'Pulse Active';
        }} else if (audioCtx.state === 'suspended') {{
            audioCtx.resume(); btn.textContent = 'Pulse Active';
        }} else {{
            audioCtx.suspend(); btn.textContent = 'Resume Pulse';
        }}
    }};
</script>
</body>
</html>"""


# ── WAV Generation ───────────────────────────────────────────────────────────

def generate_wav(params, duration=300, out_path='soul_sigil.wav'):
    v1, v2, v3, v4 = params['v1'], params['v2'], params['v3'], params['v4']
    sample_rate = 8000
    num_samples = sample_rate * duration

    print(f"Generating {duration}s WAV ({num_samples:,} samples)...")
    samples = bytearray(num_samples * 2)
    for t in range(num_samples):
        val = (t * (t >> v1 | t >> v2) & (t >> v3) & (t >> v4)) & 255
        s = int((val / 127.5 - 1.0) * 32767)
        struct.pack_into('<h', samples, t * 2, max(-32768, min(32767, s)))

    with open(out_path, 'wb') as f:
        data_size = len(samples)
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<HH', 1, 1))               # PCM, mono
        f.write(struct.pack('<II', sample_rate, sample_rate * 2))
        f.write(struct.pack('<HH', 2, 16))              # block align, bits/sample
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(samples)

    mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"WAV saved: {out_path} ({mb:.1f} MB)")


# ── Era Table ────────────────────────────────────────────────────────────────

def print_era_table(params):
    v3 = params['v3']
    sr = 8000
    era_len = 2 ** v3

    print(f"\nBeat Era Table  —  t>>{v3} mask, one era = {era_len} samples = {era_len/sr:.1f}s\n")
    print(f"  {'Era':>4}  {'t':>10}  {'Time':>7}  {'Mask':>6}  Character")
    print(f"  {'-'*4}  {'-'*10}  {'-'*7}  {'-'*6}  {'-'*24}")
    print(f"  {'0':>4}  {'0':>10}  {'0.0s':>7}  {'0':>6}  near silence (mask is zero)")
    notes = {1: "first tone — bit 0 only", 2: "bit 1 opens", 3: "interference begins",
             7: "dense harmonics", 15: "slow-evolving complexity"}
    for era in range(1, 20):
        t = era * era_len
        note = notes.get(era, "layering" if era < 7 else ("complex texture" if era < 15 else ""))
        print(f"  {era:>4}  {t:>10,}  {t/sr:>6.1f}s  {era:>6}  {note}")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Generate a hardware soul sigil — visual HTML + bytebeat WAV from your machine.'
    )
    parser.add_argument('--color1',      help='Primary color hex (e.g. #FF4400)',   default=None)
    parser.add_argument('--color2',      help='Secondary color hex (e.g. #0088FF)', default=None)
    parser.add_argument('--duration',    type=int, default=300, help='WAV duration in seconds (default: 300)')
    parser.add_argument('--no-hostname', action='store_true',   help='Exclude hostname from fingerprint')
    parser.add_argument('--out',         default='.',           help='Output directory (default: current dir)')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print()
    print("=" * 60)
    print("  Soul Sigil Generator")
    print("=" * 60)
    print()

    hw       = collect_hardware(include_hostname=not args.no_hostname)
    hash_str = hash_hardware(hw)
    print(f"Hash:    {hash_str}")

    params = derive_params(hash_str, args.color1, args.color2)
    print(f"Colors:  {params['color1']}  {params['color2']}")
    print(f"Formula: {params['formula']}\n")

    html_path = os.path.join(args.out, 'soul_sigil.html')
    wav_path  = os.path.join(args.out, 'soul_sigil.wav')

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(generate_html(params))
    print(f"HTML saved: {html_path}")

    generate_wav(params, duration=args.duration, out_path=wav_path)
    print_era_table(params)

    print("=" * 60)
    print("  Open soul_sigil.html in your browser.")
    print("=" * 60)
    print()


if __name__ == '__main__':
    main()
