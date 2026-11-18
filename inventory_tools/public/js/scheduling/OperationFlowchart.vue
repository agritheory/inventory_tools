<template>
	<div class="operation-flowchart">
		<div v-if="state.error" class="text-muted small">{{ state.error }}</div>
		<div v-else-if="!state.data || !state.data.nodes.length" class="text-muted small">
			{{ state.loading ? __('Loading operations…') : __('No operations to chart.') }}
		</div>
		<template v-else>
			<div class="operation-flowchart-header text-muted small">
				{{ formatMinutes(state.data.makespan_mins) }}
				<template v-if="state.data.release">· {{ formatDatetime(finishDatetime) }}</template>
			</div>
			<div class="operation-flowchart-canvas">
				<svg :width="layout.width" :height="layout.height" :viewBox="`0 0 ${layout.width} ${layout.height}`">
					<defs>
						<marker
							v-for="variant in ['default', 'critical']"
							:id="`flowchart-arrow-${variant}-${uid}`"
							:key="variant"
							viewBox="0 0 10 10"
							refX="9"
							refY="5"
							markerWidth="7"
							markerHeight="7"
							orient="auto-start-reverse">
							<path d="M 0 0 L 10 5 L 0 10 z" :class="`arrow-${variant}`" />
						</marker>
					</defs>
					<g :transform="`translate(0, ${layout.offsetY})`">
						<g v-for="band in layout.bands" :key="band.bom">
							<rect class="bom-band" :x="band.x" :y="band.y" :width="band.width" :height="band.height" rx="6" />
							<text class="bom-band-label" :x="band.x + 8" :y="band.y + 14">{{ band.bom }}</text>
						</g>

						<g v-for="edge in layout.edges" :key="`${edge.predecessor}-${edge.successor}`">
							<path
								:d="edge.path"
								class="edge"
								:class="{ implicit: edge.source !== 'explicit', critical: edge.critical }"
								:marker-end="`url(#flowchart-arrow-${edge.critical ? 'critical' : 'default'}-${uid})`">
								<title>{{ edge.title }}</title>
							</path>
							<text v-if="edge.label" class="edge-label" :x="edge.labelX" :y="edge.labelY" text-anchor="middle">
								{{ edge.label }}
							</text>
						</g>

						<g
							v-for="node in layout.nodes"
							:key="node.key"
							class="node"
							:class="{ critical: node.critical }"
							:transform="`translate(${node.x}, ${node.y})`"
							@click="emit('select', node.key)">
							<title>{{ node.title }}</title>
							<rect :width="NODE_WIDTH" :height="nodeHeight" rx="6" />
							<text class="node-title" x="10" y="20">{{ truncate(`${node.idx}. ${node.operation}`, 26) }}</text>
							<text class="node-detail" x="10" y="38">
								{{ truncate(node.workstation || __('No workstation'), 30) }}
							</text>
							<text class="node-detail" x="10" y="56">
								{{ formatMinutes(node.time_in_mins) }} · {{ startLabel(node) }}
							</text>
							<g v-if="node.issues.length" :transform="`translate(${NODE_WIDTH - 14}, 14)`">
								<title>{{ node.issues.map(issue => issue.message).join('\n') }}</title>
								<circle r="8" :class="node.issueSeverity" />
								<text class="badge-text" text-anchor="middle" y="4">!</text>
							</g>
						</g>
					</g>
				</svg>
			</div>
			<ul v-if="issueList.length" class="operation-flowchart-issues">
				<li
					v-for="(issue, index) in issueList"
					:key="index"
					:class="[issue.severity, { selectable: issue.node }]"
					@click="issue.node && emit('select', issue.node.key)">
					<template v-if="issue.node">{{ issue.node.idx }}. {{ issue.node.operation }}: </template>
					{{ issue.message }}
				</li>
			</ul>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type FlowchartNode = {
	key: string
	idx: number
	sequence_id: number
	operation: string
	workstation: string | null
	bom: string | null
	time_in_mins: number
	earliest_start_mins: number
	latest_start_mins: number
	slack_mins: number
	earliest_start: string | null
	critical: boolean
}

type FlowchartEdge = {
	predecessor: string
	successor: string
	relation: string
	abbreviation: string
	lag_mins: number
	source: string
	binding: boolean
	critical: boolean
}

type FlowchartIssue = { severity: string; message: string; key: string | null }

type FlowchartData = {
	doctype: string
	release: string | null
	makespan_mins: number
	nodes: FlowchartNode[]
	edges: FlowchartEdge[]
	issues: FlowchartIssue[]
}

const props = defineProps<{
	state: { data: FlowchartData | null; loading: boolean; error: string | null }
}>()
const emit = defineEmits<{ select: [key: string] }>()

const NODE_WIDTH = 210
const nodeHeight = 68
const COLUMN_GAP = 90
const ROW_GAP = 22
const PADDING = 24
const BAND_HEADER = 22
const MIN_HEIGHT = 264
const EXIT_STUB = 10
const ENTRY_STUB = 22
const LANE_BASE = 26
const LANE_STEP = 14
const LANE_CLEARANCE = 16
const LANE_LABEL_ROOM = 18
const uid = Math.random().toString(36).slice(2, 8)

const __ = (text: string) => (window as any).__(text)

const issueList = computed(() => {
	const data = props.state.data
	if (!data) return []
	const nodesByKey = Object.fromEntries(data.nodes.map(node => [node.key, node]))
	return data.issues.map(issue => ({ ...issue, node: issue.key ? nodesByKey[issue.key] : undefined }))
})

const finishDatetime = computed(() => {
	const data = props.state.data
	if (!data?.release) return null
	return frappe.datetime.add_minutes(data.release, Math.round(data.makespan_mins))
})

const layout = computed(() => {
	const data = props.state.data as FlowchartData
	const columns: FlowchartNode[][] = []
	for (const node of data.nodes) {
		const last = columns[columns.length - 1]
		if (last && last[0].sequence_id === node.sequence_id) {
			last.push(node)
		} else {
			columns.push([node])
		}
	}

	const boms = [...new Set(data.nodes.map(node => node.bom).filter(Boolean))] as string[]
	const showBands = boms.length > 1
	const top = PADDING + (showBands ? BAND_HEADER : 0)
	const columnX = (column: number) => PADDING + column * (NODE_WIDTH + COLUMN_GAP)

	const columnHeight = (rows: number) => rows * (nodeHeight + ROW_GAP) - ROW_GAP
	const tallest = Math.max(...columns.map(column => column.length))
	const height = Math.max(MIN_HEIGHT, top + columnHeight(tallest) + PADDING)
	const width = columnX(columns.length - 1) + NODE_WIDTH + PADDING
	const middle = (top + height - PADDING) / 2

	const positions: Record<string, { x: number; y: number; column: number }> = {}
	columns.forEach((column, columnIndex) => {
		const columnTop = middle - columnHeight(column.length) / 2
		column.forEach((node, row) => {
			positions[node.key] = {
				x: columnX(columnIndex),
				y: columnTop + row * (nodeHeight + ROW_GAP),
				column: columnIndex,
			}
		})
	})

	const bands = showBands
		? boms.map(bom => {
				const bomColumns = data.nodes.filter(node => node.bom === bom).map(node => positions[node.key].column)
				const first = Math.min(...bomColumns)
				const last = Math.max(...bomColumns)
				return {
					bom,
					x: columnX(first) - COLUMN_GAP / 3,
					y: PADDING / 2,
					width: columnX(last) - columnX(first) + NODE_WIDTH + (2 * COLUMN_GAP) / 3,
					height: height - PADDING,
				}
		  })
		: []

	const issuesByKey: Record<string, FlowchartIssue[]> = {}
	for (const issue of data.issues) {
		if (issue.key) (issuesByKey[issue.key] ||= []).push(issue)
	}

	const nodes = data.nodes.map(node => {
		const issues = issuesByKey[node.key] || []
		return {
			...node,
			...positions[node.key],
			issues,
			issueSeverity: issues.some(issue => issue.severity === 'error') ? 'badge-error' : 'badge-warning',
			title: [
				node.operation,
				node.workstation,
				node.critical ? __('Critical path') : `${__('Slack')} ${formatMinutes(node.slack_mins)}`,
				...issues.map(issue => issue.message),
			]
				.filter(Boolean)
				.join('\n'),
		}
	})

	const routes = data.edges.map(edge => {
		const from = positions[edge.predecessor]
		const to = positions[edge.successor]
		const [fromSide, toSide] = edge.relation.split(' to ')
		const fromRight = fromSide === 'Finish'
		const toRight = toSide === 'Finish'
		const x1 = from.x + (fromRight ? NODE_WIDTH : 0)
		const x2 = to.x + (toRight ? NODE_WIDTH : 0)
		const exitX = x1 + (fromRight ? EXIT_STUB : -EXIT_STUB)
		const entryX = x2 + (toRight ? ENTRY_STUB : -ENTRY_STUB)
		const kind = fromRight && !toRight && entryX > exitX ? 'curve' : x1 === x2 ? 'loop' : 'lane'
		return {
			edge,
			kind,
			x1,
			y1: from.y + nodeHeight / 2,
			x2,
			y2: to.y + nodeHeight / 2,
			exitX,
			entryX,
			top: Math.min(from.y, to.y),
			span: [Math.min(exitX, entryX) - LANE_CLEARANCE, Math.max(exitX, entryX) + LANE_CLEARANCE],
			level: 0,
		}
	})

	const levels: number[][][] = []
	const laneRoutes = routes.filter(route => route.kind === 'lane')
	laneRoutes.sort((a, b) => a.span[1] - a.span[0] - (b.span[1] - b.span[0]))
	for (const route of laneRoutes) {
		let level = 0
		while ((levels[level] || []).some(([lo, hi]) => route.span[0] < hi && lo < route.span[1])) {
			level++
		}
		;(levels[level] ||= []).push(route.span)
		route.level = level
	}
	const laneY = (route: (typeof routes)[number]) => route.top - LANE_BASE - route.level * LANE_STEP
	const offsetY = Math.max(0, ...laneRoutes.map(route => LANE_LABEL_ROOM - laneY(route)))

	const edges = routes.map(route => {
		const { edge, x1, y1, x2, y2, exitX, entryX } = route
		let path: string
		let labelX: number
		let labelY: number
		if (route.kind === 'curve') {
			const reach = Math.max(36, (x2 - x1) / 2)
			path = `M ${x1} ${y1} C ${x1 + reach} ${y1}, ${x2 - reach} ${y2}, ${x2} ${y2}`
			labelX = (x1 + x2) / 2
			labelY = (y1 + y2) / 2 - 6
		} else if (route.kind === 'loop') {
			path = roundedPath([
				[x1, y1],
				[exitX, y1],
				[exitX, y2],
				[x2, y2],
			])
			labelX = exitX
			labelY = (y1 + y2) / 2
		} else {
			const y = laneY(route)
			path = roundedPath([
				[x1, y1],
				[exitX, y1],
				[exitX, y],
				[entryX, y],
				[entryX, y2],
				[x2, y2],
			])
			labelX = (exitX + entryX) / 2
			labelY = y - 4
		}

		const lag = edge.lag_mins ? ` ${edge.lag_mins > 0 ? '+' : ''}${edge.lag_mins}m` : ''
		const label = edge.source === 'explicit' ? `${edge.abbreviation}${lag}` : ''
		return {
			...edge,
			path,
			label,
			labelX,
			labelY,
			title: `${edge.relation}${lag}${edge.source === 'explicit' ? '' : ` (${__('default')})`}`,
		}
	})

	return { nodes, edges, bands, width, height: height + offsetY, offsetY }
})

function roundedPath(points: [number, number][], radius = 8) {
	let path = `M ${points[0][0]} ${points[0][1]}`
	for (let index = 1; index < points.length - 1; index++) {
		const [px, py] = points[index - 1]
		const [cx, cy] = points[index]
		const [nx, ny] = points[index + 1]
		const before = Math.min(radius, Math.hypot(cx - px, cy - py) / 2)
		const after = Math.min(radius, Math.hypot(nx - cx, ny - cy) / 2)
		const inX = cx - Math.sign(cx - px) * before
		const inY = cy - Math.sign(cy - py) * before
		const outX = cx + Math.sign(nx - cx) * after
		const outY = cy + Math.sign(ny - cy) * after
		path += ` L ${inX} ${inY} Q ${cx} ${cy} ${outX} ${outY}`
	}
	const [lx, ly] = points[points.length - 1]
	return `${path} L ${lx} ${ly}`
}

function formatMinutes(minutes: number) {
	const rounded = Math.round(minutes || 0)
	if (Math.abs(rounded) < 60) return `${rounded}m`
	const hours = Math.trunc(rounded / 60)
	const remainder = Math.abs(rounded % 60)
	return remainder ? `${hours}h ${remainder}m` : `${hours}h`
}

function formatDatetime(value: string | null) {
	return value ? frappe.datetime.str_to_user(value) : ''
}

function startLabel(node: FlowchartNode) {
	if (node.earliest_start) return formatDatetime(node.earliest_start)
	return `+${formatMinutes(node.earliest_start_mins)}`
}

function truncate(text: string, length: number) {
	return text.length > length ? `${text.slice(0, length - 1)}…` : text
}
</script>

<style scoped>
.operation-flowchart {
	margin-top: var(--margin-md, 12px);
}
.operation-flowchart-header {
	margin-bottom: 4px;
}
.operation-flowchart-canvas {
	overflow-x: auto;
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius-md, 8px);
	background: var(--subtle-fg, var(--fg-color));
}
.operation-flowchart-canvas svg {
	display: block;
}
.node {
	cursor: pointer;
}
.node rect {
	fill: var(--fg-color);
	stroke: var(--border-color);
	stroke-width: 1;
}
.node.critical rect {
	stroke: var(--primary);
	stroke-width: 2;
}
.node:hover rect {
	stroke: var(--primary);
}
.node-title {
	font-size: 13px;
	font-weight: 600;
	fill: var(--text-color);
}
.node-detail {
	font-size: 11px;
	fill: var(--text-muted);
}
.badge-warning {
	fill: var(--orange-500, orange);
}
.badge-error {
	fill: var(--red-500, red);
}
.badge-text {
	font-size: 11px;
	font-weight: 700;
	fill: white;
}
.edge {
	fill: none;
	stroke: var(--gray-500, gray);
	stroke-width: 1.5;
}
.edge.implicit {
	stroke-dasharray: 5 4;
}
.edge.critical {
	stroke: var(--primary);
	stroke-width: 2;
}
.arrow-default {
	fill: var(--gray-500, gray);
}
.arrow-critical {
	fill: var(--primary);
}
.edge-label {
	font-size: 11px;
	fill: var(--text-color);
	paint-order: stroke;
	stroke: var(--subtle-fg, var(--fg-color));
	stroke-width: 4px;
}
.bom-band {
	fill: var(--subtle-accent, rgba(0, 0, 0, 0.03));
	stroke: var(--border-color);
	stroke-dasharray: 3 3;
}
.bom-band-label {
	font-size: 11px;
	fill: var(--text-muted);
}
.operation-flowchart-issues {
	margin: 8px 0 0;
	padding-left: 18px;
	font-size: 12px;
}
.operation-flowchart-issues .selectable {
	cursor: pointer;
}
.operation-flowchart-issues .warning {
	color: var(--orange-600, darkorange);
}
.operation-flowchart-issues .error {
	color: var(--red-600, darkred);
}
</style>
