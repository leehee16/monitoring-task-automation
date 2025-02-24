const fs = require('fs').promises;
const path = require('path');
const moment = require('moment');

class DataCollector {
    constructor(historyManager) {
        this.historyManager = historyManager;
        this.collectedData = [];
        this.metadata = {
            collectionStartTime: moment().format(),
            collectionEndTime: null,
            totalRecords: 0,
            filteredRecords: 0
        };
    }

    async addUserData(userData) {
        const normalizedData = {
            // 기본 사용자 정보
            id: userData.id,
            type: userData.type,
            fbUid: userData.fbUid,
            nickname: userData.nick,
            country: userData.country,
            gender: userData.gender,
            
            // 시간 정보
            lastLogin: userData.lastLogin,
            collectedAt: moment().format(),
            
            // 활동 데이터
            captures: [],
            
            // 분석용 메타데이터
            activityMetrics: {
                totalImages: 0,
                capturedDates: [],
                averageImagesPerDay: 0
            }
        };

        this.collectedData.push(normalizedData);
    }

    getUserData(fbUid) {
        return this.collectedData.find(data => data.fbUid === fbUid);
    }

    async addCaptureData(fbUid, captureInfo) {
        const userData = this.collectedData.find(data => data.fbUid === fbUid);
        if (!userData) return;

        userData.captures.push({
            date: captureInfo.date,
            userInfo: captureInfo.userInfo,
            imageCount: captureInfo.imageCount,
            capturedAt: moment().format()
        });

        // 활동 메트릭 업데이트
        userData.activityMetrics.totalImages += captureInfo.imageCount;
        userData.activityMetrics.capturedDates.push(captureInfo.date);
        userData.activityMetrics.averageImagesPerDay = 
            userData.activityMetrics.totalImages / userData.activityMetrics.capturedDates.length;
    }

    async saveToJson() {
        this.metadata.collectionEndTime = moment().format();
        this.metadata.totalRecords = this.collectedData.length;

        const analysisData = {
            metadata: this.metadata,
            users: this.collectedData,
            statistics: this.generateStatistics()
        };

        const weekDir = this.historyManager.getCurrentWeekDir();
        const outputPath = path.join(weekDir, 'analysis_data.json');
        await fs.writeFile(outputPath, JSON.stringify(analysisData, null, 2));
        return outputPath;
    }

    async saveImage(fbUid, date, imageBuffer) {
        const weekDir = this.historyManager.getCurrentWeekDir();
        const userDir = path.join(weekDir, 'data', fbUid);
        await fs.mkdir(userDir, { recursive: true });
        
        const imagePath = path.join(userDir, `${fbUid}_${date}.jpg`);
        await fs.writeFile(imagePath, imageBuffer);
        return imagePath;
    }

    generateStatistics() {
        return {
            countryDistribution: this.getCountryDistribution(),
            typeDistribution: this.getTypeDistribution(),
            genderDistribution: this.getGenderDistribution(),
            activityPatterns: this.getActivityPatterns()
        };
    }

    getCountryDistribution() {
        return this.collectedData.reduce((acc, user) => {
            acc[user.country] = (acc[user.country] || 0) + 1;
            return acc;
        }, {});
    }

    getTypeDistribution() {
        return this.collectedData.reduce((acc, user) => {
            acc[user.type] = (acc[user.type] || 0) + 1;
            return acc;
        }, {});
    }

    getGenderDistribution() {
        return this.collectedData.reduce((acc, user) => {
            acc[user.gender] = (acc[user.gender] || 0) + 1;
            return acc;
        }, {});
    }

    getActivityPatterns() {
        return this.collectedData.map(user => ({
            fbUid: user.fbUid,
            totalImages: user.activityMetrics.totalImages,
            averageImagesPerDay: user.activityMetrics.averageImagesPerDay,
            activeDays: user.activityMetrics.capturedDates.length
        }));
    }
}

module.exports = DataCollector; 