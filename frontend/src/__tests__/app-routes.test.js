const fs = require('fs');
const path = require('path');

const srcPath = (...parts) => path.join(__dirname, '..', ...parts);

describe('App route imports', () => {
  test('pilot review page component exists for App route import', () => {
    const app = fs.readFileSync(srcPath('App.js'), 'utf8');
    const pilotReviewPagePath = srcPath('components', 'PilotReviewPage.js');

    expect(app).toContain("import PilotReviewPage from './components/PilotReviewPage'");
    expect(fs.existsSync(pilotReviewPagePath)).toBe(true);
  });
});
