// Curated fix steps for each diagnostic issue_type the backend emits.
//
// Each FixEntry carries a plain-English summary and per-deployment-shape steps.
// When all three shapes share the same fix (e.g. alembic_pending: just restart
// the container), use universal_steps instead of duplicating across shape keys.
//
// Backend issue_type values originate in app/backend/sage_is_ai/routers/diagnostics.py.
//
// The DATA lives in fixRegistry.json beside this file, not in this module. Two
// readers need it now — this component, and the server-rendered diagnostics
// page, which has no bundler to import a .ts through. Keeping the remedies in
// TypeScript would have meant transcribing them into Python, and a second
// hand-typed copy of 40 remediation steps is precisely the drift this migration
// exists to delete. The types below still describe the shape.

import fixRegistryData from './fixRegistry.json';

export type DeploymentShape = 'caprover' | 'docker_compose' | 'brew' | 'unknown';

export interface FixStep {
	description_key: string; // i18n key under diagnostics.fix.<issue_type>.<shape?>.<idx>
	command?: string; // optional shell snippet — copy-only, never executed
	ui_path?: string; // optional navigation hint to a settings page
}

export interface FixEntry {
	plain_english_key: string;
	universal_steps?: FixStep[];
	caprover_steps?: FixStep[];
	docker_compose_steps?: FixStep[];
	brew_steps?: FixStep[];
}

export const fixRegistry: Record<string, FixEntry> = fixRegistryData as Record<
	string,
	FixEntry
>;

export function getStepsFor(entry: FixEntry, shape: DeploymentShape): FixStep[] {
	if (shape === 'caprover' && entry.caprover_steps) return entry.caprover_steps;
	if (shape === 'docker_compose' && entry.docker_compose_steps) return entry.docker_compose_steps;
	if (shape === 'brew' && entry.brew_steps) return entry.brew_steps;
	return entry.universal_steps ?? [];
}

export function getAllShapesFor(entry: FixEntry): Record<DeploymentShape, FixStep[]> {
	const universal = entry.universal_steps ?? [];
	return {
		caprover: entry.caprover_steps ?? universal,
		docker_compose: entry.docker_compose_steps ?? universal,
		brew: entry.brew_steps ?? universal,
		unknown: universal
	};
}

export function hasFix(issueType: string | null | undefined): boolean {
	return !!issueType && issueType in fixRegistry;
}
