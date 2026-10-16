import react from '@vitejs/plugin-react'
import { cpSync, createReadStream, existsSync, mkdirSync, statSync } from 'node:fs'
import { extname, join, normalize, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, type Plugin } from 'vite'

// The product walkthrough lives in ../docs (walkthrough.html + images/) so the README and the app share one copy.
// Serve it at /walkthrough/ in dev and copy it into dist/walkthrough/ on build.
const DOCS_DIR = fileURLToPath(new URL('../docs', import.meta.url))
const MIME: Record<string, string> = { '.html': 'text/html; charset=utf-8', '.png': 'image/png' }

function walkthrough(): Plugin {
  let outDir = 'dist'
  let isBuild = false
  return {
    name: 'walkthrough',
    configResolved(config) {
      outDir = resolve(config.root, config.build.outDir)
      isBuild = config.command === 'build'
    },
    configureServer(server) {
      server.middlewares.use('/walkthrough', (req, res, next) => {
        const path = decodeURIComponent((req.url ?? '/').split('?')[0])
        if (path === '' || path === '/') {
          if (!req.originalUrl?.split('?')[0].endsWith('/')) {
            res.writeHead(301, { Location: '/walkthrough/' }).end()
            return
          }
          res.setHeader('Content-Type', MIME['.html'])
          createReadStream(join(DOCS_DIR, 'walkthrough.html')).pipe(res)
          return
        }
        const file = normalize(join(DOCS_DIR, path))
        if (!path.startsWith('/images/') || !file.startsWith(DOCS_DIR) || !existsSync(file) || !statSync(file).isFile()) {
          next()
          return
        }
        res.setHeader('Content-Type', MIME[extname(file)] ?? 'application/octet-stream')
        createReadStream(file).pipe(res)
      })
    },
    closeBundle() {
      if (!isBuild || !existsSync(join(DOCS_DIR, 'walkthrough.html'))) return
      const dest = join(outDir, 'walkthrough')
      mkdirSync(dest, { recursive: true })
      cpSync(join(DOCS_DIR, 'walkthrough.html'), join(dest, 'index.html'))
      cpSync(join(DOCS_DIR, 'images'), join(dest, 'images'), { recursive: true })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), walkthrough()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
