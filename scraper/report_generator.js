const fs = require('fs').promises;
const path = require('path');
const moment = require('moment');

class ReportGenerator {
    constructor(scrapedData, outputDir, startTime, endTime) {
        this.scrapedData = scrapedData;
        this.outputDir = outputDir;
        this.startTime = startTime;
        this.endTime = endTime;
    }

    async generateReport() {
        const reportData = [];
        
        // 각 사용자별 데이터 수집
        for (const user of this.scrapedData) {
            const userStats = await this.getUserStats(user.fbUid);
            reportData.push({
                fbUid: user.fbUid,
                nick: user.nick,
                country: user.country,
                lastLogin: user.lastLogin,
                totalImages: userStats.totalImages,
                totalCaptureDays: userStats.totalDays
            });
        }

        // CSV 파일 생성
        const csvHeader = 'FB_UID,닉네임,국가,마지막로그인,총이미지수,캡처날짜수\n';
        const csvRows = reportData.map(row => 
            `${row.fbUid},${row.nick},${row.country},${row.lastLogin},${row.totalImages},${row.totalCaptureDays}`
        ).join('\n');

        // 폴더명에서 날짜 범위 추출
        const folderName = path.basename(this.outputDir);  // policemonitor_YYYYMMDD-YYYYMMDD
        const dateRange = folderName.split('policemonitor_')[1];  // YYYYMMDD-YYYYMMDD
        
        // 날짜가 포함된 리포트 파일명 생성
        const reportPath = path.join(this.outputDir, `report_${dateRange}.csv`);
        await fs.writeFile(reportPath, csvHeader + csvRows, 'utf-8');
        
        console.log(`리포트가 생성되었습니다: ${reportPath}`);
    }

    async getUserStats(fbUid) {
        const userDir = path.join(this.outputDir, fbUid);
        try {
            const files = await fs.readdir(userDir);
            const imageFiles = files.filter(file => file.endsWith('.jpg'));
            
            // 날짜 수 계산 (YYYYMMDD 형식에서 중복 제거)
            const uniqueDates = new Set(
                imageFiles.map(file => file.split('_')[1].replace('.jpg', ''))
            );

            return {
                totalImages: imageFiles.length,
                totalDays: uniqueDates.size
            };
        } catch (error) {
            return {
                totalImages: 0,
                totalDays: 0
            };
        }
    }
}

module.exports = ReportGenerator;
