const puppeteer = require('puppeteer');
const { scrapeLoadedPage } = require('./scraper');
const Scraper = require('./scraper');

async function main() {
  const scraper = new Scraper();

  try {
    await scraper.initialize();
    await scraper.scrapeData();
    console.log('페이지 데이터 스크래핑 완료');
  } catch (error) {
    console.error('오류 발생:', error);
  } finally {
    await scraper.close();
  }
}

main().catch(console.error);
