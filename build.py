#!/usr/bin/env python3
import argparse, json, os, pathlib


def parse_dir_name(name: str) -> dict:
    """Extract condition/severity/source/rank from dir name.

    Formats:
      clipping__en__0.4__fleurs__rankNN
      noisegap__en__3__0.4__fleurs__rankNN
      distance__en__16.0__fleurs__rankNN
      g711mu__en__g711mu__fleurs__rankNN
      gsm__en__gsm__fleurs__rankNN
      reverb__en__1.6__fleurs__rankNN
    """
    parts = name.split("__")
    condition = parts[0]
    if condition == "noisegap":
        severity = f"({parts[2]}, {parts[3]})"
        source = parts[4]
        rank = int(parts[5][4:])
    else:
        severity = parts[2]
        source = parts[3]
        rank = int(parts[4][4:])
    return {"condition": condition, "severity": severity, "source": source, "rank": rank}


def find_samples(input_dir: pathlib.Path, script_dir: pathlib.Path) -> list:
    samples = []
    for root, dirs, files in os.walk(input_dir):
        dirs.sort()
        if "clean.wav" in files and "meta.json" in files:
            sample_dir = pathlib.Path(root)
            with open(sample_dir / "meta.json") as f:
                meta = json.load(f)
            info = parse_dir_name(sample_dir.name)
            samples.append({
                **info,
                "gt_text": meta.get("gt_text_norm", ""),
                "clean_pred": meta.get("clean_model_pred_norm", ""),
                "pred_text": meta.get("pred_text_norm", ""),
                "clean_src": os.path.relpath(sample_dir / "clean.wav", script_dir),
                "degraded_src": os.path.relpath(sample_dir / "degraded.wav", script_dir),
            })
    samples.sort(key=lambda s: (s["condition"], s["source"], s["severity"], int(s["rank"])))
    return samples


HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Audio Comparison: Clean vs Degraded</title>
  <style>
    body { font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 24px; color: #222; }
    h1 { font-size: 20px; margin-bottom: 4px; }
    .subtitle { font-size: 14px; color: #888; margin-bottom: 20px; }
    .filters { display: flex; gap: 16px; align-items: center; margin-bottom: 20px; flex-wrap: wrap; }
    .filters label { font-size: 13px; color: #555; }
    .filters select { padding: 5px 10px; font-size: 14px; border: 1px solid #ccc; border-radius: 4px; margin-left: 6px; }
    #count { font-size: 13px; color: #999; margin-left: auto; }
    .card { border: 1px solid #ddd; border-radius: 8px; padding: 16px 20px; margin-bottom: 14px; background: #fafafa; }
    .card-header { font-size: 12px; color: #aaa; margin-bottom: 12px; text-transform: uppercase; letter-spacing: .06em; }
    .audio-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 14px; }
    .audio-col > .alabel { display: block; font-size: 13px; font-weight: 600; color: #555; margin-bottom: 5px; }
    audio { width: 100%; }
    .text-row { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; border-top: 1px solid #eee; padding-top: 12px; }
    .text-col > .tl { font-size: 11px; font-weight: 700; color: #bbb; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 4px; }
    .text-col > p { margin: 0; font-size: 14px; line-height: 1.6; }
    #empty { display: none; padding: 60px; text-align: center; color: #bbb; font-size: 15px; }
  </style>
</head>
<body>
  <h1>Audio Comparison: Clean vs Degraded</h1>
  <p class="subtitle">Compare original clean audio against degraded versions. Ground truth and ASR transcriptions shown below each pair.</p>
  <div class="filters">
    <label>Condition<select id="fc"></select></label>
    <label>Dataset<select id="fd"></select></label>
    <span id="count"></span>
  </div>
  <div id="cards"></div>
  <div id="empty">No samples match the selected filters.</div>
<script>
const S = /*SAMPLES*/;

const fc = document.getElementById('fc');
const fd = document.getElementById('fd');

function addOpts(sel, values, all) {
  sel.add(new Option(all, ''));
  values.forEach(v => sel.add(new Option(v, v)));
}
addOpts(fc, [...new Set(S.map(s => s.condition))].sort(), 'All conditions');
addOpts(fd, [...new Set(S.map(s => s.source))].sort(), 'All datasets');

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function render() {
  const c = fc.value, d = fd.value;
  const filtered = S.filter(s => (!c || s.condition === c) && (!d || s.source === d));
  const container = document.getElementById('cards');
  container.innerHTML = '';
  document.getElementById('empty').style.display = filtered.length ? 'none' : 'block';
  document.getElementById('count').textContent = filtered.length + ' sample' + (filtered.length !== 1 ? 's' : '');
  filtered.forEach(s => {
    const div = document.createElement('div');
    div.className = 'card';
    div.innerHTML =
      '<div class="card-header">' + esc(s.condition) + ' &nbsp;&bull;&nbsp; severity ' + esc(s.severity) + ' &nbsp;&bull;&nbsp; ' + esc(s.source) + '</div>' +
      '<div class="audio-row">' +
        '<div class="audio-col"><span class="alabel">Original (clean)</span><audio controls src="' + esc(s.clean_src) + '"></audio></div>' +
        '<div class="audio-col"><span class="alabel">Degraded</span><audio controls src="' + esc(s.degraded_src) + '"></audio></div>' +
      '</div>' +
      '<div class="text-row">' +
        '<div class="text-col"><div class="tl">Ground truth</div><p>' + esc(s.gt_text) + '</p></div>' +
        '<div class="text-col"><div class="tl">Transcription (clean)</div><p>' + esc(s.clean_pred) + '</p></div>' +
        '<div class="text-col"><div class="tl">Transcription (degraded)</div><p>' + esc(s.pred_text) + '</p></div>' +
      '</div>';
    container.appendChild(div);
  });
}

fc.addEventListener('change', render);
fd.addEventListener('change', render);
render();
</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate audio comparison HTML page.")
    parser.add_argument(
        "--input", default=None,
        help="Path to samples dir (default: ../selected relative to this script)"
    )
    args = parser.parse_args()

    script_dir = pathlib.Path(__file__).resolve().parent
    if args.input is None:
        input_dir = (script_dir / "../selected").resolve()
    else:
        input_dir = pathlib.Path(args.input).resolve()

    if not input_dir.is_dir():
        raise SystemExit(f"Input dir not found: {input_dir}")

    samples = find_samples(input_dir, script_dir)
    print(f"Found {len(samples)} samples in {input_dir}")

    html = HTML_TEMPLATE.replace("/*SAMPLES*/", json.dumps(samples, ensure_ascii=False))

    out_path = script_dir / "index.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Written: {out_path}")


if __name__ == "__main__":
    main()
