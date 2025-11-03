// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { resolve } from 'node:path'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vitejs.dev/config/
export default defineConfig({
	plugins: [vue()],
	build: {
		outDir: './inventory_tools/public/dist/js',
		target: 'esnext',
		emptyOutDir: false,
		sourcemap: true,
		lib: {
			entry: resolve(__dirname, './inventory_tools.js'),
			name: 'inventory_tools',
			fileName: format => `inventory_tools.js`,
		},
		rollupOptions: {
			output: {
				chunkFileNames: 'chunks/[name].[hash].js',
				assetFileNames: 'assets/[name].[ext]',
			},
		},
	},
	define: {
		'process.env': process.env,
	},
})
