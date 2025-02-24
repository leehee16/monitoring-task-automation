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
      
      const loginButton = await page.$('input[type="submit"][value="LogIn"]');
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
    console.log('첫 번째 메뉴 클릭');
    
    // 1초 대기 후 상태 확인
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // '?' 메뉴가 있는지 확인
    const hasQuestionMenu = await page.evaluate(() => {
        return document.querySelector('.fa-question-circle') !== null;
    });
    
    if (hasQuestionMenu) {
        await page.click('.fa-bars');
        console.log('두 번째 메뉴 클릭 (? 메뉴 닫기)');
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    // Police 메뉴가 보이는지 확인
    const isPoliceVisible = await page.evaluate(() => {
        const policeMenu = document.querySelector('#aside-police');
        if (!policeMenu) return false;
        
        const style = window.getComputedStyle(policeMenu);
        return style.display !== 'none' && style.visibility !== 'hidden';
    });

    if (!isPoliceVisible) {
        console.log('Police 메뉴가 보이지 않아 메뉴를 다시 엽니다.');
        await page.click('.fa-bars');
        await new Promise(resolve => setTimeout(resolve, 1000));
    }

    console.log('Hidden bar 열기 완료');

    // Police 메뉴가 클릭 가능할 때까지 대기
    console.log('Police 메뉴가 클릭 가능할 때까지 대기...');
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Police 메뉴 요소가 실제로 클릭 가능한지 확인
    const isClickable = await page.evaluate(() => {
        const element = document.querySelector('#aside-police');
        if (!element) return false;
        
        const rect = element.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0 && 
               window.getComputedStyle(element).display !== 'none' &&
               window.getComputedStyle(element).visibility !== 'hidden';
    });

    if (!isClickable) {
        console.log('Police 메뉴가 아직 클릭 가능하지 않습니다. 메뉴를 다시 열어봅니다.');
        await page.click('.fa-bars');
        await new Promise(resolve => setTimeout(resolve, 2000));
    }

    try {
        // Police 메뉴 클릭 시도
        await page.evaluate(() => {
            const element = document.querySelector('#aside-police');
            if (element) {
                element.click();
            } else {
                throw new Error('Police 메뉴를 찾을 수 없습니다.');
            }
        });
        console.log('Police 메뉴 클릭 완료');
        
        // 페이지 전환 대기
        await page.waitForNavigation({ waitUntil: 'networkidle0', timeout: 30000 });
    } catch (error) {
        console.error('Police 메뉴 클릭 중 오류:', error);
        throw error;
    }

    console.log('데이터 로딩 상태를 자동으로 체크합니다...');

    return { browser, page };
  } catch (error) {
    console.error('로그인 중 오류 발생:', error);
    return { error: error.message };
  }
}

module.exports = loginAndNavigate;
