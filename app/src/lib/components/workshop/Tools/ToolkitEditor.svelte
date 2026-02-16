<script>
	import { getContext, onMount, tick } from 'svelte';

	const i18n = getContext('i18n');

	import CodeEditor from '$lib/components/common/CodeEditor.svelte';
	import { goto } from '$app/navigation';
	import ConfirmDialog from '$lib/components/common/ConfirmDialog.svelte';
	import Badge from '$lib/components/common/Badge.svelte';
	import ChevronLeft from '$lib/components/icons/ChevronLeft.svelte';
	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import AccessControlModal from '../common/AccessControlModal.svelte';
	import { user } from '$lib/stores';

	let formElement = null;
	let loading = false;

	let showConfirm = false;
	let showAccessControlModal = false;

	export let edit = false;
	export let clone = false;

	export let onSave = () => {};

	export let id = '';
	export let name = '';
	export let meta = {
		description: ''
	};
	export let content = '';
	export let accessControl = {};

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
	let boilerplate = `import os
import requests
from datetime import datetime
from pydantic import BaseModel, Field

class Tools:
    def __init__(self):
        pass

    # Add your custom tools using pure Python code here, make sure to add type hints and descriptions
	
    def get_user_name_and_email_and_id(self, __user__: dict = {}) -> str:
        """
        Get the user name, Email and ID from the user object.
        """

        # Do not include a descrption for __user__ as it should not be shown in the tool's specification
        # The session user object will be passed as a parameter when the function is called

        print(__user__)
        result = ""

        if "name" in __user__:
            result += f"User: {__user__['name']}"
        if "id" in __user__:
            result += f" (ID: {__user__['id']})"
        if "email" in __user__:
            result += f" (Email: {__user__['email']})"

        if result == "":
            result = "User: Unknown"

        return result

    def get_current_time(self) -> str:
        """
        Get the current time in a more human-readable format.
        """

        now = datetime.now()
        current_time = now.strftime("%I:%M:%S %p")  # Using 12-hour format with AM/PM
        current_date = now.strftime(
            "%A, %B %d, %Y"
        )  # Full weekday, month name, day, and year

        return f"Current Date and Time = {current_date}, {current_time}"

    def calculator(
        self,
        equation: str = Field(
            ..., description="The mathematical equation to calculate."
        ),
    ) -> str:
        """
        Calculate the result of an equation.
        """

        # Avoid using eval in production code
        # https://nedbatchelder.com/blog/201206/eval_really_is_dangerous.html
        try:
            result = eval(equation)
            return f"{equation} = {result}"
        except Exception as e:
            print(e)
            return "Invalid equation"

    def get_current_weather(
        self,
        city: str = Field(
            "New York, NY", description="Get the current weather for a given city."
        ),
    ) -> str:
        """
        Get the current weather for a given city.
        """

        api_key = os.getenv("OPENWEATHER_API_KEY")
        if not api_key:
            return (
                "API key is not set in the environment variable 'OPENWEATHER_API_KEY'."
            )

        base_url = "http://api.openweathermap.org/data/2.5/weather"
        params = {
            "q": city,
            "appid": api_key,
            "units": "metric",  # Optional: Use 'imperial' for Fahrenheit
        }

        try:
            response = requests.get(base_url, params=params)
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx and 5xx)
            data = response.json()

            if data.get("cod") != 200:
                return f"Error fetching weather data: {data.get('message')}"

            weather_description = data["weather"][0]["description"]
            temperature = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            wind_speed = data["wind"]["speed"]

            return f"Weather in {city}: {temperature}°C"
        except requests.RequestException as e:
            return f"Error fetching weather data: {str(e)}"
`;

	const saveHandler = async () => {
		loading = true;
		onSave({
			id,
			name,
			meta,
			content,
			access_control: accessControl
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
				console.log('Code formatted successfully');

				saveHandler();
			}
		}
	};
</script>

<AccessControlModal
	bind:show={showAccessControlModal}
	bind:accessControl
	accessRoles={['read', 'write']}
	allowPublic={$user?.permissions?.sharing?.public_tools || $user?.role === 'admin'}
/>

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
									style="--w:100%; --ta:left; --size:0.875rem; --py:0.375rem; --px:0.25rem; --radius:0.5rem; --dark-c:var(--color-gray-300, #cdcdcd); --hvr-dark-c:#fff; --hvr-bgc:rgb(0 0 0 / 0.05); --hvr-dark-bgc:var(--color-gray-850, #262626)"
									on:click={() => {
										goto('/workshop/tools');
									}}
									type="button"
								>
									<ChevronLeft strokeWidth="2.5" />
								</button>
							</Tooltip>
						</div>

						<div style="--fx:1 1 0%">
							<Tooltip content={$i18n.t('e.g. My Tools')} placement="top-start">
								<input
									style="--w:100%; --size:1.5rem; --weight:500; --bgc:transparent; --oe:none"
	class="font-primary"
									type="text"
									placeholder={$i18n.t('Tool Name')}
									bind:value={name}
									required
								/>
							</Tooltip>
						</div>

						<div style="--as:center; --fs:0">
							<button
								style="--bgc:var(--color-gray-50, #f9f9f9); --hvr-bgc:var(--color-gray-100, #ececec); --c:#000; --dark-bgc:var(--color-gray-850, #262626); --hvr-dark-bgc:var(--color-gray-800, #333); --dark-c:#fff; --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --px:0.5rem; --py:0.25rem; --radius:9999px; --d:flex; --g:0.25rem; --ai:center"
								type="button"
								on:click={() => {
									showAccessControlModal = true;
								}}
							>
								<LockClosed strokeWidth="2.5" className="size-3.5" />

								<div style="--size:0.875rem; --weight:500; --fs:0">
									{$i18n.t('Access')}
								</div>
							</button>
						</div>
					</div>

					<div style="--d:flex; --g:0.5rem; --px:0.25rem; --ai:center">
						{#if edit}
							<div style="--size:0.875rem; --c:var(--color-gray-500, #9b9b9b); --fs:0">
								{id}
							</div>
						{:else}
							<Tooltip className="w-full" content={$i18n.t('e.g. my_tools')} placement="top-start">
								<input
									style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
	class="disabled:text-gray-500"
									type="text"
									placeholder={$i18n.t('Tool ID')}
									bind:value={id}
									required
									disabled={edit}
								/>
							</Tooltip>
						{/if}

						<Tooltip
							className="w-full self-center items-center flex"
							content={$i18n.t('e.g. Tools for performing various operations')}
							placement="top-start"
						>
							<input
								style="--w:100%; --size:0.875rem; --bgc:transparent; --oe:none"
								type="text"
								placeholder={$i18n.t('Tool Description')}
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

				<div style="--pb:0.75rem; --d:flex; --jc:space-between">
					<div style="--fx:1 1 0%; --pr:0.75rem">
						<div style="--size:0.75rem; --c:var(--color-gray-500, #9b9b9b); --line-clamp:2">
							<span style="--weight:600; --dark-c:var(--color-gray-200, #e3e3e3)">{$i18n.t('Warning:')}</span>
							{$i18n.t('Tools are a function calling system with arbitrary code execution')} <br />—
							<span style="--weight:500; --dark-c:var(--color-gray-400, #b4b4b4)"
								>{$i18n.t(`don't install random tools from sources you don't trust.`)}</span
							>
						</div>
					</div>

					<button
						style="--px:0.875rem; --py:0.375rem; --size:0.875rem; --weight:500; --bgc:#000; --hvr-bgc:var(--color-gray-900, #171717); --c:#fff; --dark-bgc:#fff; --dark-c:#000; --hvr-dark-bgc:var(--color-gray-100, #ececec); --tn:color, background-color, border-color, text-decoration-color, fill, stroke, opacity, box-shadow, transform, filter, backdrop-filter 150ms cubic-bezier(0.4, 0, 0.2, 1); --radius:9999px"
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
	<div style="--size:0.875rem; --c:var(--color-gray-500, #9b9b9b)">
		<div style="--bgc:rgb(234 179 8 / 0.2); --c:#a16207; --dark-c:#fef08a; --radius:0.5rem; --px:1rem; --py:0.75rem">
			<div>{$i18n.t('Please carefully review the following warnings:')}</div>

			<ul style="--mt:0.25rem; list-style-type:disc; --pl:1rem; --size:0.75rem">
				<li>
					{$i18n.t('Tools have a function calling system that allows arbitrary code execution.')}
				</li>
				<li>{$i18n.t('Do not install tools from sources you do not fully trust.')}</li>
			</ul>
		</div>

		<div style="--my:0.75rem">
			{$i18n.t(
				'I acknowledge that I have read and I understand the implications of my action. I am aware of the risks associated with executing arbitrary code and I have verified the trustworthiness of the source.'
			)}
		</div>
	</div>
</ConfirmDialog>
