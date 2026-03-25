<script>
	import { getContext, onMount, tick } from 'svelte';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';

	let formElement = null;
	let loading = false;
	let showConfirm = false;

	export let onSave = () => {};

	export let edit = false;
	export let clone = false;

	export let id = '';
	export let name = '';
	export let meta = {
		description: ''
	};
	export let content = '';
	let _content = '';

	$: if (content) {
		updateContent();
	}

	const updateContent = () => {
		_content = content;
	};

	$: if (name && !edit && !clone) {
		id = name.replace(/\s+/g, '_').toLowerCase();
	}

	let codeEditor;
	let boilerplate = `"""
title: Example Filter
author: open-webui
author_url: https://github.com/open-webui
funding_url: https://github.com/open-webui
version: 0.1
"""

from pydantic import BaseModel, Field
from typing import Optional


class Filter:
    class Valves(BaseModel):
        priority: int = Field(
            default=0, description="Priority level for the filter operations."
        )
        max_turns: int = Field(
            default=8, description="Maximum allowable conversation turns for a user."
        )
        pass

    class UserValves(BaseModel):
        max_turns: int = Field(
            default=4, description="Maximum allowable conversation turns for a user."
        )
        pass

    def __init__(self):
        # Indicates custom file handling logic. This flag helps disengage default routines in favor of custom
        # implementations, informing the WebUI to defer file-related operations to designated methods within this class.
        # Alternatively, you can remove the files directly from the body in from the inlet hook
        # self.file_handler = True

        # Initialize 'valves' with specific configurations. Using 'Valves' instance helps encapsulate settings,
        # which ensures settings are managed cohesively and not confused with operational flags like 'file_handler'.
        self.valves = self.Valves()
        pass

    def inlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify the request body or validate it before processing by the chat completion API.
        # This function is the pre-processor for the API where various checks on the input can be performed.
        # It can also modify the request before sending it to the API.
        print(f"inlet:{__name__}")
        print(f"inlet:body:{body}")
        print(f"inlet:user:{__user__}")

        if __user__.get("role", "admin") in ["user", "admin"]:
            messages = body.get("messages", [])

            max_turns = min(__user__["valves"].max_turns, self.valves.max_turns)
            if len(messages) > max_turns:
                raise Exception(
                    f"Conversation turn limit exceeded. Max turns: {max_turns}"
                )

        return body

    def outlet(self, body: dict, __user__: Optional[dict] = None) -> dict:
        # Modify or analyze the response body after processing by the API.
        # This function is the post-processor for the API, which can be used to modify the response
        # or perform additional checks and analytics.
        print(f"outlet:{__name__}")
        print(f"outlet:body:{body}")
        print(f"outlet:user:{__user__}")

        return body
`;

	const _boilerplate = `from pydantic import BaseModel
from typing import Optional, Union, Generator, Iterator
from open_webui.utils.misc import get_last_user_message

import os
import requests


# Filter Class: This class is designed to serve as a pre-processor and post-processor
# for request and response modifications. It checks and transforms requests and responses
# to ensure they meet specific criteria before further processing or returning to the user.
class Filter:
    class Valves(BaseModel):
        max_turns: int = 4
        pass

    def __init__(self):
        # Indicates custom file handling logic. This flag helps disengage default routines in favor of custom
        # implementations, informing the WebUI to defer file-related operations to designated methods within this class.
        # Alternatively, you can remove the files directly from the body in from the inlet hook
        self.file_handler = True

        # Initialize 'valves' with specific configurations. Using 'Valves' instance helps encapsulate settings,
        # which ensures settings are managed cohesively and not confused with operational flags like 'file_handler'.
        self.valves = self.Valves(**{"max_turns": 2})
        pass

    def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        # Modify the request body or validate it before processing by the chat completion API.
        # This function is the pre-processor for the API where various checks on the input can be performed.
        # It can also modify the request before sending it to the API.
        print(f"inlet:{__name__}")
        print(f"inlet:body:{body}")
        print(f"inlet:user:{user}")

        if user.get("role", "admin") in ["user", "admin"]:
            messages = body.get("messages", [])
            if len(messages) > self.valves.max_turns:
                raise Exception(
                    f"Conversation turn limit exceeded. Max turns: {self.valves.max_turns}"
                )

        return body

    def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        # Modify or analyze the response body after processing by the API.
        # This function is the post-processor for the API, which can be used to modify the response
        # or perform additional checks and analytics.
        print(f"outlet:{__name__}")
        print(f"outlet:body:{body}")
        print(f"outlet:user:{user}")

        messages = [
            {
                **message,
                "content": f"{message['content']} - @@Modified from Filter Outlet",
            }
            for message in body.get("messages", [])
        ]

        return {"messages": messages}



# Pipe Class: This class functions as a customizable pipeline.
# It can be adapted to work with any external or internal models,
# making it versatile for various use cases outside of just OpenAI models.
class Pipe:
    class Valves(BaseModel):
        OPENAI_API_BASE_URL: str = "https://api.openai.com/v1"
        OPENAI_API_KEY: str = "your-key"
        pass

    def __init__(self):
        self.type = "manifold"
        self.valves = self.Valves()
        self.pipes = self.get_openai_models()
        pass

    def get_openai_models(self):
        if self.valves.OPENAI_API_KEY:
            try:
                headers = {}
                headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
                headers["Content-Type"] = "application/json"

                r = requests.get(
                    f"{self.valves.OPENAI_API_BASE_URL}/models", headers=headers
                )

                models = r.json()
                return [
                    {
                        "id": model["id"],
                        "name": model["name"] if "name" in model else model["id"],
                    }
                    for model in models["data"]
                    if "gpt" in model["id"]
                ]

            except Exception as e:

                print(f"Error: {e}")
                return [
                    {
                        "id": "error",
                        "name": "Could not fetch models from OpenAI, please update the API Key in the valves.",
                    },
                ]
        else:
            return []

    def pipe(self, body: dict) -> Union[str, Generator, Iterator]:
        # This is where you can add your custom pipelines like RAG.
        print(f"pipe:{__name__}")

        if "user" in body:
            print(body["user"])
            del body["user"]

        headers = {}
        headers["Authorization"] = f"Bearer {self.valves.OPENAI_API_KEY}"
        headers["Content-Type"] = "application/json"

        model_id = body["model"][body["model"].find(".") + 1 :]
        payload = {**body, "model": model_id}
        print(payload)

        try:
            r = requests.post(
                url=f"{self.valves.OPENAI_API_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                stream=True,
            )

            r.raise_for_status()

            if body["stream"]:
                return r.iter_lines()
            else:
                return r.json()
        except Exception as e:
            return f"Error: {e}"
`;

	const saveHandler = async () => {
		loading = true;
		onSave({
			id,
			name,
			meta,
			content
		});
	};

	const submitHandler = async () => {
		if (codeEditor) {
			content = _content;
			await tick();

			const res = await codeEditor.formatPythonCodeHandler();
			await tick();

			content = _content;
			await tick();

			if (res) {
				console.info('Code formatted successfully');

				saveHandler();
			}
		}
	};
</script>

<div style="--d:flex; --fd:column; --jc:space-between; --w:100%; --ofy:auto; --h:100%">
	<div style="--mx:auto; --w:100%; --px-md:0; --h:100%">
		<form
			bind:this={formElement}
			style="--d:flex; --fd:column; --maxh:100dvh; --h:100%"
			on:submit|preventDefault={() => {
				if (edit) {
					submitHandler();
				} else {
					showConfirm = true;
				}
			}}
		>
			<div style="--d:flex; --fd:column; --fx:1 1 0%; --of:auto; --h:0; --radius:0.5rem">
				<div style="--w:100%; --mb:0.5rem; --d:flex; --fd:column; --g:0.125rem">
					<div style="--d:flex; --w:100%; --ai:center">
						<div style="--fs:0; --mr:0.5rem">
							<Tooltip content={$i18n.t('Back')}>
								<button
									style="--w:100%; --ta:left; --size:0.8rem; --py:0.4rem; --px:0.2rem; --radius:0.5rem; --dark-c:var(--color-gray-300); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:var(--color-gray-850)"
									on:click={() => {
										goto('/admin/functions');
									}}
									type="button"
								>
									<ChevronLeft strokeWidth="2.5" />
								</button>
							</Tooltip>
						</div>

						<div style="--fx:1 1 0%">
							<Tooltip content={$i18n.t('e.g. My Filter')} placement="top-start">
								<input
									style="--w:100%; --size:1.5rem; --weight:500; --bgc:transparent; --oe:none"
	class="font-primary"
									type="text"
									placeholder={$i18n.t('Function Name')}
									bind:value={name}
									required
								/>
							</Tooltip>
						</div>

						<div>
							<Badge type="muted" content={$i18n.t('Function')} />
						</div>
					</div>

					<div style="--d:flex; --g:0.5rem; --px:0.2rem; --ai:center">
						{#if edit}
							<div style="--size:0.8rem; --c:var(--color-gray-500); --fs:0">
								{id}
							</div>
						{:else}
							<Tooltip className="w-full" content={$i18n.t('e.g. my_filter')} placement="top-start">
								<input
									style="--w:100%; --size:0.8rem; --bgc:transparent; --oe:none"
	class="disabled:text-gray-500"
									type="text"
									placeholder={$i18n.t('Function ID')}
									bind:value={id}
									required
									disabled={edit}
								/>
							</Tooltip>
						{/if}

						<Tooltip
							className="w-full self-center items-center flex"
							content={$i18n.t('e.g. A filter to remove profanity from text')}
							placement="top-start"
						>
							<input
								style="--w:100%; --size:0.8rem; --bgc:transparent; --oe:none"
								type="text"
								placeholder={$i18n.t('Function Description')}
								bind:value={meta.description}
								required
							/>
						</Tooltip>
					</div>
				</div>

				<div style="--mb:0.5rem; --fx:1 1 0%; --of:auto; --h:0; --radius:0.5rem">
					<CodeEditor
						bind:this={codeEditor}
						value={content}
						lang="python"
						{boilerplate}
						onChange={(e) => {
							_content = e;
						}}
						onSave={async () => {
							if (formElement) {
								formElement.requestSubmit();
							}
						}}
					/>
				</div>

				<div style="--pb:0.6rem; --d:flex; --jc:space-between">
					<div style="--fx:1 1 0%; --pr:0.6rem">
						<div style="--size:0.6rem; --c:var(--color-gray-500); --line-clamp:2">
							<span style="--weight:600; --dark-c:var(--color-gray-200)">{$i18n.t('Warning:')}</span>
							{$i18n.t('Functions allow arbitrary code execution.')} <br />—
							<span style="--weight:500; --dark-c:var(--color-gray-400)"
								>{$i18n.t(`don't install random functions from sources you don't trust.`)}</span
							>
						</div>
					</div>

					<button
						style="--px:0.8rem; --py:0.4rem; --size:0.8rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
						type="submit"
					>
						{$i18n.t('Save')}
					</button>
				</div>
			</div>
		</form>
	</div>
</div>

<ConfirmDialog
	bind:show={showConfirm}
	on:confirm={() => {
		submitHandler();
	}}
>
	<div style="--size:0.8rem; --c:var(--color-gray-500)">
		<div style="--bgc:rgb(234 179 8 / 0.2); --c:#a16207; --dark-c:#fef08a; --radius:0.5rem; --px:1rem; --py:0.6rem">
			<div>{$i18n.t('Please carefully review the following warnings:')}</div>

			<ul style="--mt:0.2rem; list-style-type:disc; --pl:1rem; --size:0.6rem">
				<li>{$i18n.t('Functions allow arbitrary code execution.')}</li>
				<li>{$i18n.t('Do not install functions from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div style="--my:0.6rem">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>
