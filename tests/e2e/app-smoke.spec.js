import { expect, test } from '@playwright/test';

const apiBaseUrl = process.env.API_BASE_URL || 'http://127.0.0.1:5011';

async function deleteProject(request, projectId) {
  await request.post(`${apiBaseUrl}/api/delete_project`, {
    data: { project_id: projectId }
  });
}

test('app shell and navigation render without page crashes', async ({ page }) => {
  const pageErrors = [];
  page.on('pageerror', (error) => pageErrors.push(error.message));

  await page.goto('/');
  await expect(page.locator('.sidebar')).toBeVisible();
  await expect(page.locator('.main-content')).toBeVisible();
  await expect(page.locator('.brand-name')).toContainText('Content Maximizer');

  await page.locator('[data-page="business-growth-strategy"]').click();
  await expect(page.locator('.main-content')).toContainText(/Business Growth Strategy/i);

  await page.locator('[data-page="script-management"]').click();
  await expect(page.locator('.main-content')).toContainText(/Script/i);

  await page.locator('[data-page="ai-engine"]').click();
  await expect(page.locator('.main-content')).toContainText(/AI Engine|Model|Key/i);

  expect(pageErrors).toEqual([]);
});

test('project save, list, load, delete, and invalid-id guardrail work', async ({ page, request }) => {
  const timestamp = Date.now();
  const title = `Smoke Project ${timestamp}`;
  let projectId;

  const health = await request.get(`${apiBaseUrl}/api/health`);
  expect(health.status()).toBe(200);

  const saveResponse = await request.post(`${apiBaseUrl}/api/save_project`, {
    data: {
      type: 'content-maximizer',
      title,
      video_id: `smoke-video-${timestamp}`,
      transcript: 'Short smoke transcript',
      clips: [],
      blog: { title: 'Smoke Blog', sections: [] },
      social: {}
    }
  });
  expect(saveResponse.status()).toBe(200);
  const savePayload = await saveResponse.json();
  expect(savePayload.success).toBe(true);
  projectId = savePayload.project_id;

  try {
    const listResponse = await request.get(`${apiBaseUrl}/api/list_projects`);
    expect(listResponse.status()).toBe(200);
    const listPayload = await listResponse.json();
    expect(listPayload.projects.some((project) => project.id === projectId)).toBe(true);

    const getResponse = await request.get(`${apiBaseUrl}/api/get_project/${encodeURIComponent(projectId)}`);
    expect(getResponse.status()).toBe(200);
    const getPayload = await getResponse.json();
    expect(getPayload.success).toBe(true);
    expect(getPayload.data.title).toBe(`CM - ${title}`);

    const invalidGet = await request.get(`${apiBaseUrl}/api/get_project/bad$id`);
    expect(invalidGet.status()).toBe(400);

    const invalidDelete = await request.post(`${apiBaseUrl}/api/delete_project`, {
      data: { project_id: '../outside' }
    });
    expect(invalidDelete.status()).toBe(400);

    await page.goto('/');
    const projectItem = page.locator(`.project-item[data-id="${projectId}"]`);
    await expect(projectItem).toBeVisible();
    await expect(projectItem).toContainText(`CM - ${title}`);
    await projectItem.click();
    await expect(page.locator('.brand-name')).toContainText('Content Maximizer');
    await expect(page.locator('.main-content')).toContainText(/Video Clips|Written Content/i);
  } finally {
    if (projectId) {
      await deleteProject(request, projectId);
    }
  }

  const afterDelete = await request.get(`${apiBaseUrl}/api/list_projects`);
  const afterDeletePayload = await afterDelete.json();
  expect(afterDeletePayload.projects.some((project) => project.id === projectId)).toBe(false);
});
