const fs = require('fs').promises;
const path = require('path');
const moment = require('moment');

class HistoryManager {
    constructor(baseDir) {
        this.baseDir = baseDir;
        this.historyDir = path.join(baseDir, 'history');
        this.historyFile = path.join(this.historyDir, 'user_history.json');
        this.userHistory = new Map();
        this.currentWeekDir = null;
    }

    async initialize() {
        // history 디렉토리 생성
        await fs.mkdir(this.historyDir, { recursive: true });
        
        // 현재 주의 디렉토리 설정
        const startOfWeek = moment().subtract(1, 'week').startOf('isoWeek');
        const endOfWeek = moment(startOfWeek).endOf('isoWeek');
        const weekDirName = `${startOfWeek.format('YYYYMMDD')}-${endOfWeek.format('YYYYMMDD')}`;
        this.currentWeekDir = path.join(this.historyDir, weekDirName);
        
        // 주간 디렉토리 구조 생성
        await this.createWeeklyDirectoryStructure();
        
        // 기존 히스토리 파일 로드
        try {
            const historyData = await fs.readFile(this.historyFile, 'utf8');
            const history = JSON.parse(historyData);
            
            Object.entries(history).forEach(([fbUid, data]) => {
                this.userHistory.set(fbUid, data);
            });
            
            console.log(`${this.userHistory.size}개의 사용자 히스토리를 로드했습니다.`);
        } catch (error) {
            console.log('새로운 히스토리 파일을 생성합니다.');
        }
    }

    async createWeeklyDirectoryStructure() {
        // 주간 디렉토리 생성
        await fs.mkdir(this.currentWeekDir, { recursive: true });
        
        // 하위 디렉토리 생성
        await fs.mkdir(path.join(this.currentWeekDir, 'data'), { recursive: true });
        await fs.mkdir(path.join(this.currentWeekDir, 'classified'), { recursive: true });
    }

    async moveToClassified(fbUid, problemDates) {
        const sourceDir = path.join(this.currentWeekDir, 'data', fbUid);
        const targetDir = path.join(this.currentWeekDir, 'classified', fbUid);
        
        try {
            // classified 디렉토리에 사용자 폴더 생성
            await fs.mkdir(targetDir, { recursive: true });
            
            // 문제가 있는 날짜의 이미지만 이동
            const files = await fs.readdir(sourceDir);
            for (const file of files) {
                const date = file.split('_')[1]?.split('.')[0];
                if (date && problemDates.includes(date)) {
                    await fs.rename(
                        path.join(sourceDir, file),
                        path.join(targetDir, file)
                    );
                }
            }
            
            // 원본 디렉토리가 비어있으면 삭제
            const remainingFiles = await fs.readdir(sourceDir);
            if (remainingFiles.length === 0) {
                await fs.rmdir(sourceDir);
            }
        } catch (error) {
            console.error(`파일 이동 중 오류 발생: ${error}`);
        }
    }

    async updateUserHistory(userData, weekData) {
        const fbUid = userData.fbUid;
        const existingHistory = this.userHistory.get(fbUid) || {
            firstDetected: moment().format('YYYY-MM-DD'),
            detectionCount: 0,
            detectionWeeks: [],
            captures: [],
            lastUpdate: null
        };

        // 이번 주 데이터 추가
        const weekKey = moment().startOf('isoWeek').format('YYYY-MM-DD');
        if (!existingHistory.detectionWeeks.includes(weekKey)) {
            existingHistory.detectionWeeks.push(weekKey);
            existingHistory.detectionCount++;
        }

        // 캡처 데이터 추가
        weekData.captures.forEach(capture => {
            if (!existingHistory.captures.some(c => c.date === capture.date)) {
                existingHistory.captures.push(capture);
            }
        });

        // 메타데이터 업데이트
        existingHistory.lastUpdate = moment().format();
        existingHistory.lastType = userData.type;
        existingHistory.lastCountry = userData.country;
        existingHistory.consecutiveWeeks = this.calculateConsecutiveWeeks(existingHistory.detectionWeeks);

        this.userHistory.set(fbUid, existingHistory);
        await this.saveHistory();

        return existingHistory;
    }

    calculateConsecutiveWeeks(weeks) {
        if (weeks.length === 0) return 0;
        
        const sortedWeeks = weeks.sort();
        let consecutive = 1;
        let maxConsecutive = 1;
        
        for (let i = 1; i < sortedWeeks.length; i++) {
            const curr = moment(sortedWeeks[i]);
            const prev = moment(sortedWeeks[i-1]);
            
            if (curr.diff(prev, 'weeks') === 1) {
                consecutive++;
                maxConsecutive = Math.max(maxConsecutive, consecutive);
            } else {
                consecutive = 1;
            }
        }
        
        return maxConsecutive;
    }

    async saveHistory() {
        const historyObject = Object.fromEntries(this.userHistory);
        await fs.writeFile(
            this.historyFile,
            JSON.stringify(historyObject, null, 2)
        );
    }

    getExistingUserData(fbUid) {
        return this.userHistory.get(fbUid);
    }

    async markUserProcessed(fbUid, weekKey) {
        const history = this.userHistory.get(fbUid);
        if (history) {
            history.processedWeeks = history.processedWeeks || [];
            if (!history.processedWeeks.includes(weekKey)) {
                history.processedWeeks.push(weekKey);
                await this.saveHistory();
            }
        }
    }

    getCurrentWeekDir() {
        return this.currentWeekDir;
    }

    async generateHistoryReport() {
        const report = {
            totalUsers: this.userHistory.size,
            usersByConsecutiveWeeks: {},
            usersByTotalDetections: {},
            recentActivity: []
        };

        this.userHistory.forEach((history, fbUid) => {
            // 연속 주간 탐지 통계
            const consecutive = history.consecutiveWeeks || 0;
            report.usersByConsecutiveWeeks[consecutive] = 
                (report.usersByConsecutiveWeeks[consecutive] || 0) + 1;

            // 총 탐지 횟수 통계
            const totalDetections = history.detectionCount;
            report.usersByTotalDetections[totalDetections] = 
                (report.usersByTotalDetections[totalDetections] || 0) + 1;

            // 최근 활동 (지난 4주)
            if (moment(history.lastUpdate).isAfter(moment().subtract(4, 'weeks'))) {
                report.recentActivity.push({
                    fbUid,
                    lastUpdate: history.lastUpdate,
                    consecutiveWeeks: consecutive,
                    totalDetections: totalDetections,
                    type: history.lastType,
                    country: history.lastCountry
                });
            }
        });

        // 리포트 저장
        const reportPath = path.join(
            this.currentWeekDir,
            `history_report_${moment().format('YYYYMMDD')}.json`
        );
        await fs.writeFile(reportPath, JSON.stringify(report, null, 2));
        
        return report;
    }

    async updateClassification(fbUid, classification, problemDates) {
        const history = this.userHistory.get(fbUid);
        if (history) {
            history.classification = {
                type: classification,
                problemDates: problemDates,
                lastUpdate: moment().format()
            };
            
            // 연속된 문제 발생 주차 계산
            const weeks = new Set(problemDates.map(date => 
                moment(date, 'YYYYMMDD').startOf('isoWeek').format('YYYY-MM-DD')
            ));
            history.consecutiveProblemWeeks = weeks.size;
            
            await this.saveHistory();
            return true;
        }
        return false;
    }

    async updateClassificationsFromExcel(excelPath) {
        try {
            const XLSX = require('xlsx');
            const workbook = XLSX.readFile(excelPath);
            const sheet = workbook.Sheets[workbook.SheetNames[0]];
            const data = XLSX.utils.sheet_to_json(sheet, {header: 1});
            
            let updatedCount = 0;
            for (const [fbUid, classificationData] of data) {
                const [classification, problemDatesStr] = classificationData.split('_');
                const problemDates = problemDatesStr ? problemDatesStr.split(',') : [];
                
                if (await this.updateClassification(fbUid, classification, problemDates)) {
                    updatedCount++;
                }
            }
            
            console.log(`${updatedCount}개의 사용자 분류 정보가 업데이트되었습니다.`);
            return updatedCount;
        } catch (error) {
            console.error('분류 정보 업데이트 중 오류 발생:', error);
            throw error;
        }
    }

    getClassificationSummary() {
        const summary = {
            totalClassified: 0,
            byType: {},
            byProblemWeeks: {},
            recentProblems: []
        };

        this.userHistory.forEach((history, fbUid) => {
            if (history.classification) {
                summary.totalClassified++;
                
                // 분류 유형별 통계
                const type = history.classification.type;
                summary.byType[type] = (summary.byType[type] || 0) + 1;
                
                // 문제 주차별 통계
                const problemWeeks = history.consecutiveProblemWeeks || 0;
                summary.byProblemWeeks[problemWeeks] = 
                    (summary.byProblemWeeks[problemWeeks] || 0) + 1;
                
                // 최근 4주 내 문제가 있는 사용자
                const lastUpdate = moment(history.classification.lastUpdate);
                if (lastUpdate.isAfter(moment().subtract(4, 'weeks'))) {
                    summary.recentProblems.push({
                        fbUid,
                        type,
                        problemDates: history.classification.problemDates,
                        lastUpdate: history.classification.lastUpdate
                    });
                }
            }
        });

        return summary;
    }
}

module.exports = HistoryManager; 