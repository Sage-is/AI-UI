// Curated fix steps for each diagnostic issue_type the backend emits.
//
// Each FixEntry carries a plain-English summary and per-deployment-shape steps.
// When all three shapes share the same fix (e.g. alembic_pending: just restart
// the container), use universal_steps instead of duplicating across shape keys.
//
// Backend issue_type values originate in app/backend/sage_is_ai/routers/diagnostics.py.

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

export const fixRegistry: Record<string, FixEntry> = {
	endpoint_unreachable: {
		plain_english_key: 'diagnostics.fix.endpoint_unreachable.plain',
		caprover_steps: [
			{
				description_key: 'diagnostics.fix.endpoint_unreachable.caprover.0',
				ui_path: 'Admin → Settings → Connections'
			},
			{
				description_key: 'diagnostics.fix.endpoint_unreachable.caprover.1'
			},
			{
				description_key: 'diagnostics.fix.endpoint_unreachable.caprover.2'
			}
		],
		docker_compose_steps: [
			{
				description_key: 'diagnostics.fix.endpoint_unreachable.docker_compose.0'
			},
			{
				description_key: 'diagnostics.fix.endpoint_unreachable.docker_compose.1',
				command: 'docker compose down && docker compose up -d'
			}
		],
		brew_steps: [
			{
				description_key: 'diagnostics.fix.endpoint_unreachable.brew.0',
				command: 'ai-ui stop'
			},
			{
				description_key: 'diagnostics.fix.endpoint_unreachable.brew.1'
			},
			{
				description_key: 'diagnostics.fix.endpoint_unreachable.brew.2',
				command: 'ai-ui start'
			}
		]
	},

	endpoint_degraded: {
		plain_english_key: 'diagnostics.fix.endpoint_degraded.plain',
		universal_steps: [
			{
				description_key: 'diagnostics.fix.endpoint_degraded.universal.0'
			},
			{
				description_key: 'diagnostics.fix.endpoint_degraded.universal.1'
			}
		]
	},

	secret_key_ephemeral: {
		plain_english_key: 'diagnostics.fix.secret_key_ephemeral.plain',
		caprover_steps: [
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.caprover.0',
				command: 'head -c 32 /dev/random | base64',
				ui_path: 'Apps → App Configs → Environmental Variables'
			},
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.caprover.1'
			},
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.caprover.2'
			}
		],
		docker_compose_steps: [
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.docker_compose.0',
				command: 'head -c 32 /dev/random | base64'
			},
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.docker_compose.1'
			},
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.docker_compose.2',
				command: 'docker compose down && docker compose up -d'
			}
		],
		brew_steps: [
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.brew.0',
				command: 'head -c 32 /dev/random | base64'
			},
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.brew.1'
			},
			{
				description_key: 'diagnostics.fix.secret_key_ephemeral.brew.2',
				command: 'ai-ui restart'
			}
		]
	},

	alembic_pending: {
		plain_english_key: 'diagnostics.fix.alembic_pending.plain',
		caprover_steps: [
			{
				description_key: 'diagnostics.fix.alembic_pending.caprover.0',
				ui_path: 'Apps → <your-app> → Deployment → Force Rebuild & Restart'
			}
		],
		docker_compose_steps: [
			{
				description_key: 'diagnostics.fix.alembic_pending.docker_compose.0',
				command: 'docker compose restart'
			}
		],
		brew_steps: [
			{
				description_key: 'diagnostics.fix.alembic_pending.brew.0',
				command: 'ai-ui restart'
			}
		]
	},

	alembic_ahead: {
		plain_english_key: 'diagnostics.fix.alembic_ahead.plain',
		universal_steps: [
			{
				description_key: 'diagnostics.fix.alembic_ahead.universal.0'
			},
			{
				description_key: 'diagnostics.fix.alembic_ahead.universal.1'
			},
			{
				description_key: 'diagnostics.fix.alembic_ahead.universal.2'
			}
		]
	},

	data_not_writable: {
		plain_english_key: 'diagnostics.fix.data_not_writable.plain',
		caprover_steps: [
			{
				description_key: 'diagnostics.fix.data_not_writable.caprover.0',
				ui_path: 'Apps → <your-app> → App Configs → Persistent Directories'
			},
			{
				description_key: 'diagnostics.fix.data_not_writable.caprover.1'
			}
		],
		docker_compose_steps: [
			{
				description_key: 'diagnostics.fix.data_not_writable.docker_compose.0'
			},
			{
				description_key: 'diagnostics.fix.data_not_writable.docker_compose.1',
				command: 'sudo chown -R 1000:1000 ./data'
			}
		],
		brew_steps: [
			{
				description_key: 'diagnostics.fix.data_not_writable.brew.0',
				command: 'chmod -R u+rw "$HOME/Library/Application Support/ai-ui"'
			}
		]
	},

	static_asset_missing: {
		plain_english_key: 'diagnostics.fix.static_asset_missing.plain',
		caprover_steps: [
			{
				description_key: 'diagnostics.fix.static_asset_missing.caprover.0',
				ui_path: 'Apps → <your-app> → Deployment → Force Rebuild & Restart'
			}
		],
		docker_compose_steps: [
			{
				description_key: 'diagnostics.fix.static_asset_missing.docker_compose.0',
				command: 'docker compose pull && docker compose up -d --force-recreate'
			}
		],
		brew_steps: [
			{
				description_key: 'diagnostics.fix.static_asset_missing.brew.0',
				command: 'ai-ui update'
			}
		]
	},

	permissions_policy_invalid: {
		plain_english_key: 'diagnostics.fix.permissions_policy_invalid.plain',
		caprover_steps: [
			{
				description_key: 'diagnostics.fix.permissions_policy_invalid.caprover.0',
				ui_path: 'Apps → <your-app> → App Configs → Environmental Variables'
			},
			{
				description_key: 'diagnostics.fix.permissions_policy_invalid.caprover.1'
			}
		],
		docker_compose_steps: [
			{
				description_key: 'diagnostics.fix.permissions_policy_invalid.docker_compose.0'
			},
			{
				description_key: 'diagnostics.fix.permissions_policy_invalid.docker_compose.1',
				command: 'docker compose down && docker compose up -d'
			}
		],
		brew_steps: [
			{
				description_key: 'diagnostics.fix.permissions_policy_invalid.brew.0'
			}
		]
	},

	csp_missing: {
		plain_english_key: 'diagnostics.fix.csp_missing.plain',
		universal_steps: [
			{
				description_key: 'diagnostics.fix.csp_missing.universal.0'
			},
			{
				description_key: 'diagnostics.fix.csp_missing.universal.1'
			}
		]
	}
};

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
