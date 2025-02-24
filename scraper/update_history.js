const { program } = require('commander');
const { HistoryManager } = require('./HistoryManager');

program
    .option('--excel <path>', 'Excel file path containing classification results')
    .parse(process.argv);

const options = program.opts();

async function main() {
    try {
        const historyManager = new HistoryManager();
        await historyManager.initialize();
        
        console.log('분류 결과를 history에 업데이트합니다...');
        const updatedCount = await historyManager.updateClassificationsFromExcel(options.excel);
        
        console.log(`총 ${updatedCount}개의 사용자 분류 정보가 업데이트되었습니다.`);
        
        // 분류 통계 출력
        const summary = historyManager.getClassificationSummary();
        console.log('\n=== 분류 통계 ===');
        console.log(`총 분류된 사용자: ${summary.totalClassified}명`);
        
        console.log('\n분류 유형별 통계:');
        for (const [type, count] of Object.entries(summary.byType)) {
            console.log(`${type}: ${count}명`);
        }
        
        console.log('\n연속 문제 주차별 통계:');
        for (const [weeks, count] of Object.entries(summary.byProblemWeeks)) {
            console.log(`${weeks}주: ${count}명`);
        }
        
        if (summary.recentProblems.length > 0) {
            console.log('\n최근 4주 내 문제 발생 사용자:');
            for (const user of summary.recentProblems) {
                console.log(`- ${user.fbUid} (${user.type}): ${user.problemDates.join(', ')}`);
            }
        }
        
        process.exit(0);
    } catch (error) {
        console.error('오류 발생:', error);
        process.exit(1);
    }
}

main(); 