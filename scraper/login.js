const puppeteer = require('puppeteer');

async function loginAndNavigate(url, id, password) {
  try {
    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox']
    });
    const page = await browser.newPage();
    await page.goto(url);

    // 이미 로그인되어 있는지 확인
    const isLoggedIn = await page.evaluate(() => {
      return document.querySelector('.fa-bars') !== null;
    });

    if (!isLoggedIn) {
      // 로그인 과정
      await page.waitForSelector('input[placeholder="username"]', { timeout: 5000 });
      await page.type('input[placeholder="username"]', id);
      await page.type('input[placeholder="password"]', password);
      
      const loginButton = await page.$('input[type="submit"][value="Log In"]');
      if (loginButton) {
        await loginButton.click();
        console.log('로그인 버튼 클릭');
      } else {
        console.log('로그인 버튼을 찾을 수 없습니다. 폼 제출을 시도합니다.');
        await page.evaluate(() => {
          document.querySelector('form').submit();
        });
      }

      await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 30000 });
      console.log('로그인 완료');
    } else {
      console.log('이미 로그인되어 있습니다.');
    }

    // hidden bar 열기
    await page.waitForSelector('.fa-bars', { visible: true, timeout: 30000 });
    await page.click('.fa-bars');
    console.log('Hidden bar 열기 완료');

    // Police 메뉴 클릭
    await new Promise(resolve => setTimeout(resolve, 5000));
    
    const policeButton = await page.waitForSelector('#aside-police', { visible: true, timeout: 30000 });
    if (policeButton) {
      await policeButton.click();
      console.log('Police 메뉴 클릭 완료');
      
      // 페이지 전환 대기
      await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 30000 });
    } else {
      throw new Error('Police 메뉴를 찾을 수 없습니다.');
    }

    console.log('데이터 로딩 상태를 자동으로 체크합니다...');

    return { browser, page };
  } catch (error) {
    console.error('로그인 중 오류 발생:', error);
    return { error: error.message };
  }
}

module.exports = loginAndNavigate;
