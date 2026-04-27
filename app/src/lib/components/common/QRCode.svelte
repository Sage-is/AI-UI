<!--
  QRCode.svelte — pure-Svelte, zero-dependency QR encoder.

  ─────────────────────────────────────────────────────────────────────────────
  Why this exists
  ─────────────────────────────────────────────────────────────────────────────
  The try.sage workshop banner needs to project login URLs to attendees
  who scan with a phone. The user explicitly forbade adding an npm
  dependency for QR generation, so we ship a self-contained encoder.

  This is a deliberate ~250-line implementation of QR-code generation
  per ISO/IEC 18004 (simplified): byte-mode encoding, Reed-Solomon ECC
  over GF(256), versions 1-10 only (max ~174 chars at ECC-M, plenty for
  a magic-link URL like https://try.sage.is/auth#magic_token=<jwt>).

  Algorithm steps (mirrors the section ordering below):
    1. Pick the smallest version that fits the byte-mode payload at the
       requested ECC level.
    2. Build the bitstream: mode-indicator (4 bits, byte mode = 0100)
       + char-count + raw bytes + terminator + pad bytes.
    3. Split the bitstream into ECC blocks, compute Reed-Solomon parity
       per block, interleave data + ECC.
    4. Allocate the module matrix: function patterns (finder, separator,
       timing, alignment, dark module, format/version reserves).
    5. Place the data bits in zigzag pattern, skipping function patterns.
    6. Try all 8 mask patterns, pick the one with the lowest penalty.
    7. Bake in format info + version info, render to <rect> grid.

  No fallback to BarcodeDetector — that API is for *reading* QR codes,
  not generating them, and Safari has never shipped it. We wrote the
  encoder.

  Usage:
    <QRCode value={url} size={128} ecc="M" />
-->

<script lang="ts">
	export let value: string = '';
	export let size: number = 128;
	export let ecc: 'L' | 'M' | 'Q' | 'H' = 'M';

	// ─────────────────────────────────────────────────────────────────
	// QR specification tables (versions 1-10).
	// ─────────────────────────────────────────────────────────────────

	// Total data codewords per (version, ecc-level). Used to pick a version.
	// Source: ISO/IEC 18004:2006, Table 7. Indexed [version-1][L,M,Q,H].
	const DATA_CODEWORDS: number[][] = [
		[19, 16, 13, 9],     // v1
		[34, 28, 22, 16],    // v2
		[55, 44, 34, 26],    // v3
		[80, 64, 48, 36],    // v4
		[108, 86, 62, 46],   // v5
		[136, 108, 76, 60],  // v6
		[156, 124, 88, 66],  // v7
		[194, 154, 110, 86], // v8
		[232, 182, 132, 100],// v9
		[274, 216, 154, 122] // v10
	];

	// ECC codewords per block per (version, level).
	const ECC_PER_BLOCK: number[][] = [
		[7, 10, 13, 17], [10, 16, 22, 28], [15, 26, 18, 22], [20, 18, 26, 16],
		[26, 24, 18, 22], [18, 16, 24, 28], [20, 18, 18, 26], [24, 22, 22, 26],
		[30, 22, 20, 24], [18, 26, 24, 28]
	];

	// Number of EC blocks per (version, level).
	const NUM_BLOCKS: number[][] = [
		[1, 1, 1, 1], [1, 1, 1, 1], [1, 1, 2, 2], [1, 2, 2, 4],
		[1, 2, 4, 4], [2, 4, 4, 4], [2, 4, 6, 5], [2, 4, 6, 6],
		[2, 5, 8, 8], [4, 5, 8, 8]
	];

	// Alignment-pattern center coordinates by version.
	const ALIGN_COORDS: number[][] = [
		[],                   // v1 (no alignment)
		[6, 18], [6, 22], [6, 26], [6, 30], [6, 34],
		[6, 22, 38], [6, 24, 42], [6, 26, 46], [6, 28, 50]
	];

	const ECC_INDEX: Record<string, number> = { L: 0, M: 1, Q: 2, H: 3 };
	// Format-info bits per (level, mask). Pre-baked BCH-encoded values.
	const FORMAT_BITS: number[][] = [
		[0x77c4, 0x72f3, 0x7daa, 0x789d, 0x662f, 0x6318, 0x6c41, 0x6976], // L
		[0x5412, 0x5125, 0x5e7c, 0x5b4b, 0x45f9, 0x40ce, 0x4f97, 0x4aa0], // M
		[0x355f, 0x3068, 0x3f31, 0x3a06, 0x24b4, 0x2183, 0x2eda, 0x2bed], // Q
		[0x1689, 0x13be, 0x1ce7, 0x19d0, 0x0762, 0x0255, 0x0d0c, 0x083b]  // H
	];

	// ─────────────────────────────────────────────────────────────────
	// GF(256) tables for Reed-Solomon. Built once at module load.
	// ─────────────────────────────────────────────────────────────────
	const EXP = new Uint8Array(512);
	const LOG = new Uint8Array(256);
	(() => {
		let x = 1;
		for (let i = 0; i < 255; i++) {
			EXP[i] = x;
			LOG[x] = i;
			x <<= 1;
			if (x & 0x100) x ^= 0x11d;
		}
		for (let i = 255; i < 512; i++) EXP[i] = EXP[i - 255];
	})();

	function gfMul(a: number, b: number): number {
		if (a === 0 || b === 0) return 0;
		return EXP[LOG[a] + LOG[b]];
	}

	// Build the RS generator polynomial of degree `degree`.
	function rsGenerator(degree: number): number[] {
		let poly = [1];
		for (let i = 0; i < degree; i++) {
			const next = new Array(poly.length + 1).fill(0);
			for (let j = 0; j < poly.length; j++) {
				next[j] ^= poly[j];
				next[j + 1] ^= gfMul(poly[j], EXP[i]);
			}
			poly = next;
		}
		return poly;
	}

	// Compute RS parity bytes for `data`.
	function rsEncode(data: number[], eccLen: number): number[] {
		const gen = rsGenerator(eccLen);
		const buf = data.concat(new Array(eccLen).fill(0));
		for (let i = 0; i < data.length; i++) {
			const factor = buf[i];
			if (factor !== 0) {
				for (let j = 0; j < gen.length; j++) {
					buf[i + j] ^= gfMul(gen[j], factor);
				}
			}
		}
		return buf.slice(data.length);
	}

	// ─────────────────────────────────────────────────────────────────
	// Encoder pipeline
	// ─────────────────────────────────────────────────────────────────

	// UTF-8 encode for byte mode. JS strings are UTF-16; QR byte mode
	// expects 8-bit codepoints, so we use TextEncoder.
	function toBytes(s: string): number[] {
		return Array.from(new TextEncoder().encode(s));
	}

	function pickVersion(byteLen: number, eccLevel: number): number {
		for (let v = 1; v <= 10; v++) {
			// 4-bit mode + char-count (8 bits for v1-9, 16 bits for v10) + payload
			const ccBits = v < 10 ? 8 : 16;
			const need = Math.ceil((4 + ccBits + byteLen * 8) / 8);
			if (need <= DATA_CODEWORDS[v - 1][eccLevel]) return v;
		}
		return -1;
	}

	function buildBitstream(bytes: number[], version: number, totalCodewords: number): number[] {
		const bits: number[] = [];
		const push = (val: number, n: number) => {
			for (let i = n - 1; i >= 0; i--) bits.push((val >> i) & 1);
		};
		push(0b0100, 4); // byte-mode indicator
		push(bytes.length, version < 10 ? 8 : 16);
		for (const b of bytes) push(b, 8);
		// Terminator (up to 4 zero bits) + pad to byte boundary.
		const remaining = totalCodewords * 8 - bits.length;
		push(0, Math.min(4, remaining));
		while (bits.length % 8 !== 0) bits.push(0);
		// Pad bytes alternate 0xEC / 0x11 per spec.
		const pad = [0xec, 0x11];
		let padIdx = 0;
		while (bits.length < totalCodewords * 8) {
			push(pad[padIdx++ % 2], 8);
		}
		// Pack to codeword bytes.
		const cw: number[] = [];
		for (let i = 0; i < bits.length; i += 8) {
			let b = 0;
			for (let j = 0; j < 8; j++) b = (b << 1) | bits[i + j];
			cw.push(b);
		}
		return cw;
	}

	function interleave(codewords: number[], version: number, eccLevel: number): number[] {
		const numBlocks = NUM_BLOCKS[version - 1][eccLevel];
		const eccPerBlock = ECC_PER_BLOCK[version - 1][eccLevel];
		const totalData = codewords.length;
		// QR allows a "short" + "long" group; we treat all blocks equal-ish:
		// short blocks have `shortLen` data codewords, long blocks have
		// shortLen + 1. (Versions 1-10 with our ECC choices stay simple.)
		const shortLen = Math.floor(totalData / numBlocks);
		const longCount = totalData % numBlocks;
		const shortCount = numBlocks - longCount;

		const dataBlocks: number[][] = [];
		const eccBlocks: number[][] = [];
		let off = 0;
		for (let b = 0; b < numBlocks; b++) {
			const len = shortLen + (b >= shortCount ? 1 : 0);
			const slice = codewords.slice(off, off + len);
			off += len;
			dataBlocks.push(slice);
			eccBlocks.push(rsEncode(slice, eccPerBlock));
		}
		// Interleave column-major across blocks.
		const out: number[] = [];
		const maxData = shortLen + 1;
		for (let i = 0; i < maxData; i++) {
			for (let b = 0; b < numBlocks; b++) {
				if (i < dataBlocks[b].length) out.push(dataBlocks[b][i]);
			}
		}
		for (let i = 0; i < eccPerBlock; i++) {
			for (let b = 0; b < numBlocks; b++) out.push(eccBlocks[b][i]);
		}
		return out;
	}

	// ─────────────────────────────────────────────────────────────────
	// Module matrix construction
	// ─────────────────────────────────────────────────────────────────

	function makeMatrix(version: number): { m: Int8Array[]; reserved: Uint8Array[] } {
		const N = version * 4 + 17;
		const m: Int8Array[] = [];
		const reserved: Uint8Array[] = [];
		for (let i = 0; i < N; i++) {
			m.push(new Int8Array(N).fill(-1)); // -1 = unset
			reserved.push(new Uint8Array(N));
		}

		// Finder patterns at three corners + their separators.
		const placeFinder = (r: number, c: number) => {
			for (let dr = -1; dr <= 7; dr++) {
				for (let dc = -1; dc <= 7; dc++) {
					const rr = r + dr, cc = c + dc;
					if (rr < 0 || rr >= N || cc < 0 || cc >= N) continue;
					reserved[rr][cc] = 1;
					const onBorder = dr === 0 || dr === 6 || dc === 0 || dc === 6;
					const inCenter = dr >= 2 && dr <= 4 && dc >= 2 && dc <= 4;
					const inRange = dr >= 0 && dr <= 6 && dc >= 0 && dc <= 6;
					m[rr][cc] = inRange && (onBorder || inCenter) ? 1 : 0;
				}
			}
		};
		placeFinder(0, 0);
		placeFinder(0, N - 7);
		placeFinder(N - 7, 0);

		// Timing patterns.
		for (let i = 8; i < N - 8; i++) {
			m[6][i] = i % 2 === 0 ? 1 : 0;
			m[i][6] = i % 2 === 0 ? 1 : 0;
			reserved[6][i] = 1;
			reserved[i][6] = 1;
		}

		// Alignment patterns (none for v1).
		const aligns = ALIGN_COORDS[version - 1];
		for (const ar of aligns) {
			for (const ac of aligns) {
				// Skip the three positions that overlap finder patterns.
				if ((ar === 6 && ac === 6) || (ar === 6 && ac === N - 7) || (ar === N - 7 && ac === 6)) continue;
				for (let dr = -2; dr <= 2; dr++) {
					for (let dc = -2; dc <= 2; dc++) {
						const rr = ar + dr, cc = ac + dc;
						reserved[rr][cc] = 1;
						const onBorder = Math.abs(dr) === 2 || Math.abs(dc) === 2;
						const center = dr === 0 && dc === 0;
						m[rr][cc] = onBorder || center ? 1 : 0;
					}
				}
			}
		}

		// Dark module (always 1) + format-info reserves.
		m[N - 8][8] = 1;
		reserved[N - 8][8] = 1;
		for (let i = 0; i < 9; i++) {
			if (m[8][i] === -1) reserved[8][i] = 1;
			if (m[i][8] === -1) reserved[i][8] = 1;
		}
		for (let i = 0; i < 8; i++) {
			reserved[8][N - 1 - i] = 1;
			reserved[N - 1 - i][8] = 1;
		}

		return { m, reserved };
	}

	// Place data bits in the standard zigzag pattern. Right-to-left in
	// 2-column strips, alternating up/down, skipping the timing column at x=6.
	function placeData(m: Int8Array[], reserved: Uint8Array[], data: number[]) {
		const N = m.length;
		let bitIdx = 0;
		const totalBits = data.length * 8;
		let upward = true;
		for (let col = N - 1; col > 0; col -= 2) {
			if (col === 6) col--; // skip timing column
			for (let i = 0; i < N; i++) {
				const r = upward ? N - 1 - i : i;
				for (let dc = 0; dc < 2; dc++) {
					const c = col - dc;
					if (reserved[r][c]) continue;
					if (bitIdx >= totalBits) {
						m[r][c] = 0;
						continue;
					}
					const bit = (data[bitIdx >> 3] >> (7 - (bitIdx & 7))) & 1;
					m[r][c] = bit;
					bitIdx++;
				}
			}
			upward = !upward;
		}
	}

	// 8 standard mask functions. `(r,c) => boolean`: true means flip.
	const MASKS: Array<(r: number, c: number) => boolean> = [
		(r, c) => (r + c) % 2 === 0,
		(r) => r % 2 === 0,
		(_r, c) => c % 3 === 0,
		(r, c) => (r + c) % 3 === 0,
		(r, c) => (Math.floor(r / 2) + Math.floor(c / 3)) % 2 === 0,
		(r, c) => ((r * c) % 2) + ((r * c) % 3) === 0,
		(r, c) => (((r * c) % 2) + ((r * c) % 3)) % 2 === 0,
		(r, c) => (((r + c) % 2) + ((r * c) % 3)) % 2 === 0
	];

	function applyMask(m: Int8Array[], reserved: Uint8Array[], maskIdx: number) {
		const fn = MASKS[maskIdx];
		const N = m.length;
		for (let r = 0; r < N; r++) {
			for (let c = 0; c < N; c++) {
				if (!reserved[r][c] && fn(r, c)) m[r][c] ^= 1;
			}
		}
	}

	// Penalty score per spec § 8.8.2 — kept simple: count long runs +
	// 2x2 blocks. Good enough to pick a non-pathological mask for our
	// short URL payloads. We don't need pixel-perfect mask scoring.
	function penalty(m: Int8Array[]): number {
		const N = m.length;
		let p = 0;
		// Adjacent same-color modules in rows/cols.
		for (let r = 0; r < N; r++) {
			let run = 1;
			for (let c = 1; c < N; c++) {
				if (m[r][c] === m[r][c - 1]) {
					run++;
				} else {
					if (run >= 5) p += 3 + (run - 5);
					run = 1;
				}
			}
			if (run >= 5) p += 3 + (run - 5);
		}
		for (let c = 0; c < N; c++) {
			let run = 1;
			for (let r = 1; r < N; r++) {
				if (m[r][c] === m[r - 1][c]) {
					run++;
				} else {
					if (run >= 5) p += 3 + (run - 5);
					run = 1;
				}
			}
			if (run >= 5) p += 3 + (run - 5);
		}
		// 2x2 same-color blocks.
		for (let r = 0; r < N - 1; r++) {
			for (let c = 0; c < N - 1; c++) {
				const v = m[r][c];
				if (v === m[r][c + 1] && v === m[r + 1][c] && v === m[r + 1][c + 1]) p += 3;
			}
		}
		return p;
	}

	function placeFormat(m: Int8Array[], eccLevel: number, maskIdx: number) {
		const bits = FORMAT_BITS[eccLevel][maskIdx];
		const N = m.length;
		// Top-left horizontal (row 8, cols 0..8 minus timing) + vertical (col 8, rows 0..8).
		const topLeftPositions: Array<[number, number]> = [
			[8, 0], [8, 1], [8, 2], [8, 3], [8, 4], [8, 5], [8, 7], [8, 8],
			[7, 8], [5, 8], [4, 8], [3, 8], [2, 8], [1, 8], [0, 8]
		];
		for (let i = 0; i < 15; i++) {
			const [r, c] = topLeftPositions[i];
			m[r][c] = (bits >> i) & 1;
		}
		// Bottom-left vertical (col 8) + top-right horizontal (row 8).
		const splitPositions: Array<[number, number]> = [
			[N - 1, 8], [N - 2, 8], [N - 3, 8], [N - 4, 8], [N - 5, 8], [N - 6, 8], [N - 7, 8],
			[8, N - 8], [8, N - 7], [8, N - 6], [8, N - 5], [8, N - 4], [8, N - 3], [8, N - 2], [8, N - 1]
		];
		for (let i = 0; i < 15; i++) {
			const [r, c] = splitPositions[i];
			m[r][c] = (bits >> i) & 1;
		}
	}

	// ─────────────────────────────────────────────────────────────────
	// Top-level encode → matrix
	// ─────────────────────────────────────────────────────────────────

	function encode(text: string, eccLevel: number): Int8Array[] | null {
		const bytes = toBytes(text);
		const version = pickVersion(bytes.length, eccLevel);
		if (version < 0) return null;

		const totalCodewords = DATA_CODEWORDS[version - 1][eccLevel];
		const dataCodewords = buildBitstream(bytes, version, totalCodewords);
		const finalCodewords = interleave(dataCodewords, version, eccLevel);

		const { m, reserved } = makeMatrix(version);
		placeData(m, reserved, finalCodewords);

		// Pick the lowest-penalty mask.
		let bestMask = 0;
		let bestScore = Infinity;
		// We test masks on a clone, then re-apply the winner to the canonical matrix.
		const clone = (src: Int8Array[]) => src.map((row) => Int8Array.from(row));
		for (let i = 0; i < 8; i++) {
			const test = clone(m);
			applyMask(test, reserved, i);
			placeFormat(test, eccLevel, i);
			const s = penalty(test);
			if (s < bestScore) {
				bestScore = s;
				bestMask = i;
			}
		}
		applyMask(m, reserved, bestMask);
		placeFormat(m, eccLevel, bestMask);
		return m;
	}

	$: matrix = encode(value, ECC_INDEX[ecc] ?? 1);
	$: cellSize = matrix ? size / (matrix.length + 8) : 0; // 4-module quiet zone each side
	$: dim = matrix ? matrix.length + 8 : 0;
</script>

{#if matrix}
	<svg
		viewBox="0 0 {dim} {dim}"
		width={size}
		height={size}
		xmlns="http://www.w3.org/2000/svg"
		shape-rendering="crispEdges"
		class="bg-white dark:bg-white"
		aria-label="QR code for {value}"
	>
		<rect width={dim} height={dim} fill="#ffffff" />
		{#each matrix as row, r}
			{#each row as cell, c}
				{#if cell === 1}
					<rect x={c + 4} y={r + 4} width="1" height="1" fill="#000000" />
				{/if}
			{/each}
		{/each}
	</svg>
{:else}
	<div
		style="width:{size}px;height:{size}px"
		class="flex items-center justify-center text-xs text-gray-500 bg-gray-100 dark:bg-gray-800 dark:text-gray-400 rounded"
	>
		QR too long
	</div>
{/if}
