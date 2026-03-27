import { Plugin } from 'vite';
import fs from 'fs';
import path from 'path';

/**
 * Vite 插件：在开发模式下使用 index-mobile.html 作为入口
 */
export function mobileEntryPlugin(): Plugin {
  return {
    name: 'mobile-entry',
    configureServer(server) {
      return () => {
        server.middlewares.use((req, res, next) => {
          // 拦截 HTML 请求
          if (req.url === '/' || req.url === '/index.html') {
            // 读取 index-mobile.html 并让 Vite 处理
            const htmlPath = path.resolve(__dirname, 'index-mobile.html');
            let html = fs.readFileSync(htmlPath, 'utf-8');

            // 应用 Vite 的 HTML 转换
            res.setHeader('Content-Type', 'text/html');
            server.transformIndexHtml(req.url, html).then((transformedHtml) => {
              res.end(transformedHtml);
            }).catch(() => {
              res.end(html);
            });
            return;
          }
          next();
        });
      };
    },
  };
}
