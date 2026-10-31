// 교본·소식지 PDF → e-book 쪽 이미지(WebP) 변환 — ego-browser 로 실행
//   1) python3 tools/devserver.py          (다른 터미널에서 켜 두기)
//   2) ego-browser nodejs < tools/convert_pdfs.mjs
//   3) python3 web_builder.py              (ebook/index.json 서재 목록 갱신)
// 이미 변환된 문서(ebook/<id>/meta.json 있음)는 건너뜁니다. 다시 만들려면 해당 폴더를 지우고 실행하세요.
// ego-browser 의 Node 는 작업 폴더를 모르므로 저장소 경로를 아래에 적어 둡니다.
const REPO = "/Users/user/projects/hy_edu";

const fs = await import("node:fs/promises");
const exists = async (p) => fs.access(p).then(() => true, () => false);
const docs = [
  ["unit01", "/original/pdf/unit01_status.pdf"], ["unit02", "/original/pdf/unit02_history.pdf"],
  ["unit03", "/original/pdf/unit03_policy.pdf"], ["unit04", "/original/pdf/unit04_hr.pdf"],
  ["unit05", "/original/pdf/unit05_asset.pdf"], ["unit06", "/original/pdf/unit06_medical_law.pdf"],
  ["unit07", "/original/pdf/unit07_nhis.pdf"], ["kichul", "/original/pdf/kichul_2023-2025.pdf"],
];
for (const f of (await fs.readdir(REPO + "/data/2026_webzine/pdfs")).sort()) {
  const m = f.match(/^(\d+)호_/);
  if (m) docs.push(["webzine-" + m[1], "/data/2026_webzine/pdfs/" + encodeURIComponent(f)]);
}
const todo = [];
for (const d of docs) if (!(await exists(`${REPO}/ebook/${d[0]}/meta.json`))) todo.push(d);
console.log("변환할 문서:", todo.map((d) => d[0]).join(", ") || "없음");

if (todo.length) {
  const task = await taskSpace("hy_edu ebook convert");
  const page = task.page("p1");
  await page.cdp("Emulation.setDeviceMetricsOverride", { width: 1200, height: 900, deviceScaleFactor: 1, mobile: false });
  for (const [id, pdf] of todo) {
    const q = id.startsWith("webzine") ? 0.72 : 0.8;
    await page.goto(`http://127.0.0.1:8765/tools/pdf2webp.html?pdf=${pdf}&id=${id}&width=1400&q=${q}`);
    await page.waitForFunction(() => ["done", "error"].includes(document.body.dataset.state), undefined, { timeout: 1500000 });
    const st = await page.evaluate(() => document.body.dataset.state + " " + document.body.dataset.total + "쪽");
    console.log(id, st);
  }
  await task.finish({ keep: [] });
}
