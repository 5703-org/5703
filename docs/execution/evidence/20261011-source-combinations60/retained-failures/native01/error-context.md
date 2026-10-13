# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: proof60.spec.ts >> real mock worker source combination publishes, then honest partial preserves answer and draft through reload
- Location: proof60.spec.ts:12:5

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByRole('button', { name: 'Retry response', exact: true })
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('button', { name: 'Retry response', exact: true }) with timeout 5000ms
  - waiting for getByRole('button', { name: 'Retry response', exact: true })

```

```yaml
- link "Skip to content":
  - /url: "#main-content"
- complementary:
  - link "Learning Assistant":
    - /url: /chat
  - button "Close sidebar"
  - button "New chat"
  - button "Learning workspace"
  - text: Your conversations
  - button "Show archived conversations"
  - navigation "Conversations":
    - button "What is photosynthesis?"
  - navigation "Account and settings":
    - button "Learning preferences"
    - button "Learning memory"
    - button "S Second Demo Learner Learner"
    - button "Sign out"
- banner: Learning Assistant What is photosynthesis? Demo (mock model)
- main:
  - heading "What is photosynthesis?" [level=1]
  - button "Conversation actions"
  - article: You What is photosynthesis?
  - article:
    - text: Learning Assistant Demo (mock model) · Intermediate profile applied Textbook sources
    - paragraph:
      - text: Light supplies energy to convert carbon dioxide and water into sugars.
      - button "Open source 1": "[1]"
      - text: Oxygen is released.
      - button "Open source 1": "[1]"
    - button "Sources 1"
    - button "Copy"
    - button "Bookmark answer"
    - button "Feedback"
    - group: Applied preferences and response details
  - article: You What is photosynthesis? Response failed
  - status:
    - paragraph: The response could not be completed.
    - alert:
      - paragraph: The proposed answer did not pass its required support or teaching checks
      - group: Error details
  - text: Message Learning Assistant
  - textbox "Message Learning Assistant":
    - /placeholder: Ask a question, or explore an idea…
    - text: My unsent follow-up remains local after the partial source check.
  - text: Answer source
  - combobox "Answer source":
    - option "Textbook sources" [selected]
    - option "General knowledge"
  - text: Teaching style
  - combobox "Teaching style":
    - option "Direct explanation" [selected]
    - option "Get a hint"
  - checkbox "Intermediate explanations" [checked]
  - text: Intermediate explanations
  - button "Send message"
  - button "Start a new problem"
  - paragraph: Demo responses use a mock model. Check the sources and verify important details.
```

# Test source

```ts
  15  |   const requests: { method: string; path: string }[] = [];
  16  |   const unexpected: { method: string; origin: string }[] = [];
  17  |   await page.route('**/*', route => {
  18  |     const request = route.request();
  19  |     const address = new URL(request.url());
  20  |     if (![UI, API].includes(address.origin)) {
  21  |       unexpected.push({ method: request.method(), origin: address.origin });
  22  |       return route.abort('blockedbyclient');
  23  |     }
  24  |     if (address.pathname.startsWith('/api/')) {
  25  |       requests.push({ method: request.method(), path: address.pathname });
  26  |     }
  27  |     // The real API supplies every response; no authored GET replacement applies.
  28  |     return route.continue();
  29  |   });
  30  |   await page.goto('/login');
  31  |   await page.getByLabel('Email', { exact: true }).fill('student2@example.com');
  32  |   await page.getByLabel('Password', { exact: true }).fill('Passw0rd!');
  33  |   await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  34  |   const composer = page.getByRole('textbox', { name: 'Message Learning Assistant' });
  35  |   await expect(composer).toBeVisible();
  36  |   await expect(page.getByText('Demo (mock model)', { exact: true }).first()).toBeVisible();
  37  |   const post = page.waitForResponse(response => response.request().method() === 'POST'
  38  |     && response.url().endsWith('/messages'));
  39  |   await composer.fill('What is photosynthesis?');
  40  |   const started = performance.now();
  41  |   await page.getByRole('button', { name: 'Send message', exact: true }).click();
  42  |   const submitted = await post;
  43  |   expect(submitted.status()).toBe(202);
  44  |   const first = (await submitted.json()).data;
  45  |   const oldAnswer = page.locator('[data-answer-id]').last();
  46  |   await expect(oldAnswer).toBeVisible({ timeout: 30000 });
  47  |   await expect(oldAnswer.locator('.prose')).toContainText(COMPLETE);
  48  |   await expect(oldAnswer.locator('.prose')).toContainText(PROTECTED);
  49  |   const mockTFull = performance.now() - started;
  50  |   await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0);
  51  |   await expect(page).toHaveURL(/\/chat\/[0-9a-f-]+$/);
  52  |   const sessionId = new URL(page.url()).pathname.split('/')[2];
  53  |   const answerId = await oldAnswer.getAttribute('data-answer-id');
  54  |   expect(answerId).toBeTruthy();
  55  |   const token = await page.evaluate(() => sessionStorage.getItem('cs30.access-token'));
  56  |   expect(typeof token).toBe('string');
  57  |   const api = async (route: string) => {
  58  |     const result = await page.request.get(`${API}/api/v1${route}`, {
  59  |       headers: { Authorization: `Bearer ${token}` },
  60  |     });
  61  |     expect(result.ok()).toBe(true);
  62  |     return (await result.json()).data;
  63  |   };
  64  |   const answer = await api(`/answers/${answerId}`);
  65  |   const firstJob = await api(`/jobs/${first.job_id}`);
  66  |   expect(firstJob.state).toBe('succeeded');
  67  |   expect(firstJob.answer_id).toBe(answerId);
  68  |   expect(answer.request_id).toBe(first.request_id);
  69  |   expect(answer.model_mode).toBe('mock');
  70  |   expect(answer.response.answer_text).toBe(`${COMPLETE} [ev_001] ${PROTECTED} [ev_001]`);
  71  |   expect(answer.response.citations.length).toBeGreaterThan(0);
  72  |   const opened = page.waitForResponse(response => response.request().method() === 'POST'
  73  |     && response.url().endsWith(`/answers/${answerId}/exposures`)
  74  |     && response.request().postDataJSON()?.kind === 'citation_opened');
  75  |   await oldAnswer.getByRole('button', { name: 'Open source 1' }).first().click();
  76  |   await expect(page.getByRole('dialog', { name: 'Sources' })).toBeVisible();
  77  |   const openResponse = await opened;
  78  |   expect(openResponse.ok()).toBe(true);
  79  |   const view = (await openResponse.json()).data.citation_view;
  80  |   expect(view.evidence_id).toBe(answer.response.citations[0]);
  81  |   await expect(page.locator('.source-passage')).toHaveText(
  82  |     view.segments.map((part: { text: string }) => part.text).join(''),
  83  |   );
  84  |   await page.screenshot({ path: testInfo.outputPath('success-source.png'), fullPage: true });
  85  |   await page.keyboard.press('Escape');
  86  |   await expect(page.getByRole('dialog', { name: 'Sources' })).toHaveCount(0);
  87  |   const evidenceHashes: Record<string, string> = {};
  88  |   for (const identity of answer.response.citations) {
  89  |     const evidence = await api(`/answers/${answerId}/evidence/${identity}`);
  90  |     evidenceHashes[identity] = evidence.text_hash;
  91  |   }
  92  |   await page.reload();
  93  |   await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  94  |   await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', answerId!);
  95  |   await expect(page.locator('.assistant-message .prose')).toContainText(COMPLETE);
  96  |   await expect(page.locator('.assistant-message .prose')).toContainText(PROTECTED);
  97  |   await fs.writeFile(path.join(directory, 'success-dom.txt'), await page.locator('body').innerText(), { flag: 'wx' });
  98  |   await page.screenshot({ path: testInfo.outputPath('success-reload.png'), fullPage: true });
  99  | 
  100 |   const secondPost = page.waitForResponse(response => response.request().method() === 'POST'
  101 |     && response.url().endsWith('/messages'));
  102 |   await composer.fill('What is photosynthesis?');
  103 |   await page.getByRole('button', { name: 'Send message', exact: true }).click();
  104 |   const secondResponse = await secondPost;
  105 |   expect(secondResponse.status()).toBe(202);
  106 |   const second = (await secondResponse.json()).data;
  107 |   // This edits only the ordinary client draft, never the frozen submitted request.
  108 |   await composer.fill(DRAFT);
  109 |   await expect(page.getByText('The response could not be completed.', { exact: true })).toBeVisible({ timeout: 30000 });
  110 |   const secondJob = await api(`/jobs/${second.job_id}`);
  111 |   expect(secondJob.state).toBe('failed');
  112 |   expect(secondJob.answer_id).toBeNull();
  113 |   expect(secondJob.error.code).toBe('SEMANTIC_CHECK_FAILED');
  114 |   await expect(page.getByText(secondJob.error.message, { exact: true })).toBeVisible();
> 115 |   await expect(page.getByRole('button', { name: 'Retry response', exact: true })).toBeVisible();
      |                                                                                   ^ Error: expect(locator).toBeVisible() failed
  116 |   await expect(page.getByRole('button', { name: 'Stop generation', exact: true })).toHaveCount(0);
  117 |   await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  118 |   await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', answerId!);
  119 |   await expect(page.locator('.assistant-message .prose')).toContainText(COMPLETE);
  120 |   await expect(composer).toHaveValue(DRAFT);
  121 |   await page.screenshot({ path: testInfo.outputPath('partial-failure.png'), fullPage: true });
  122 |   await page.waitForTimeout(1700);
  123 |   expect(requests.filter(row => row.method === 'POST' && row.path.endsWith('/messages'))).toHaveLength(2);
  124 |   expect(requests.filter(row => row.method === 'POST' && row.path.endsWith('/retry'))).toHaveLength(0);
  125 |   await page.reload();
  126 |   await expect(page.getByText('The response could not be completed.', { exact: true })).toBeVisible();
  127 |   await expect(page.getByText(secondJob.error.message, { exact: true })).toBeVisible();
  128 |   await expect(page.getByRole('button', { name: 'Retry response', exact: true })).toBeVisible();
  129 |   await expect(page.locator('[data-answer-id]')).toHaveCount(1);
  130 |   await expect(page.locator('[data-answer-id]').last()).toHaveAttribute('data-answer-id', answerId!);
  131 |   await expect(page.locator('.assistant-message .prose')).toContainText(COMPLETE);
  132 |   await expect(composer).toHaveValue(DRAFT);
  133 |   const history = await api(`/sessions/${sessionId}/messages?limit=100`);
  134 |   const savedAnswers = history.items.filter((row: { answer?: { id: string } }) => row.answer);
  135 |   expect(savedAnswers).toHaveLength(1);
  136 |   expect(savedAnswers[0].answer.id).toBe(answerId);
  137 |   expect(history.latest_job_id).toBe(second.job_id);
  138 |   expect(requests.filter(row => row.method === 'POST' && row.path.endsWith('/messages'))).toHaveLength(2);
  139 |   expect(requests.filter(row => row.method === 'POST' && row.path.endsWith('/retry'))).toHaveLength(0);
  140 |   expect(unexpected).toEqual([]);
  141 |   await fs.writeFile(path.join(directory, 'partial-reload-dom.txt'), await page.locator('body').innerText(), { flag: 'wx' });
  142 |   await page.screenshot({ path: testInfo.outputPath('partial-reload.png'), fullPage: true });
  143 |   await fs.writeFile(path.join(directory, 'proof60-browser-receipt.json'), JSON.stringify({
  144 |     session_id: sessionId,
  145 |     success: { request_id: first.request_id, job_id: first.job_id, answer_id: answerId,
  146 |       response: answer.response, cited_evidence_ids: answer.response.citations,
  147 |       evidence_hashes: evidenceHashes, mock_send_to_complete_dom_ms: mockTFull },
  148 |     partial: { request_id: second.request_id, job_id: second.job_id, error_code: secondJob.error.code,
  149 |       old_answer_id: answerId, old_answer_preserved: true, draft_preserved_on_reload: true },
  150 |     message_posts: requests.filter(row => row.method === 'POST' && row.path.endsWith('/messages')).length,
  151 |     automatic_retry_posts: requests.filter(row => row.method === 'POST' && row.path.endsWith('/retry')).length,
  152 |     unexpected_origins: unexpected, requests, model_mode: 'mock', actual_browser_api_worker: true,
  153 |     scientific_quality_claim: false, live_model_t_full_ms: null,
  154 |   }, null, 2), { flag: 'wx' });
  155 | });
  156 | 
```