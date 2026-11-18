import { createServer } from "node:http";
import { access } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import sirv from "sirv";
import { attachWar } from "../preview/server/war.js";

const dist = new URL("../dist/", import.meta.url);
await access(new URL("war.html", dist)).catch(() => {
  throw new Error("請先執行 npm run build 建立遊戲檔案。");
});
const host = process.env.HOST || "127.0.0.1";
const port = Number(process.env.PORT || 4174);
const server = createServer(sirv(fileURLToPath(dist), { etag: true }));
attachWar(server);
server.listen(port, host, () => {
  console.log(`神燼主神戰 http://${host}:${server.address().port}/war.html`);
});
