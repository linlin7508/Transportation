class PasserbyFight {
    constructor(config) {
        this.urls = config.urls;
        this.selectedCreatureId = null;
        this.selectedCreature = null;
        this.location = null;
        this.matchToken = null;
        this.statusTimer = null;
        this.fallbackTimer = null;
    }

    init() {
        this.loadUserCreatures();
    }

    openModal() {
        new bootstrap.Modal(document.getElementById('spriteModal')).show();
    }

    loadUserCreatures() {
        const creatureList = document.getElementById('creature-list');
        creatureList.innerHTML = `
            <div class="col-12 text-center py-4">
                <div class="spinner-border text-warning" role="status"></div>
                <p class="mt-2">正在載入你的精靈...</p>
            </div>
        `;

        fetch('/game/api/user/creatures')
            .then(response => response.json())
            .then(data => {
                creatureList.innerHTML = '';
                if (!Array.isArray(data) || data.length === 0) {
                    creatureList.innerHTML = `
                        <div class="col-12 text-center py-4">
                            <p class="text-muted">你還沒有可出戰精靈</p>
                            <a href="${this.urls.catch}" class="btn btn-warning">去捕捉精靈</a>
                        </div>
                    `;
                    return;
                }

                data.forEach(creature => {
                    creatureList.appendChild(this.createCreatureCard(creature));
                });
            })
            .catch(error => {
                console.error('載入精靈失敗:', error);
                creatureList.innerHTML = '<div class="col-12 text-center text-danger">載入精靈失敗</div>';
            });
    }

    createCreatureCard(creature) {
        const div = document.createElement('div');
        div.className = 'col-md-4 col-sm-6 mb-3';
        const imageUrl = creature.image_url || '/static/img/Data/%E8%99%9B%E5%BC%B1%E5%85%94.png';
        const element = creature.element || creature.type || creature.element_type || 'normal';
        div.innerHTML = `
            <div class="card creature-card h-100">
                <img src="${imageUrl}" class="card-img-top" alt="${creature.name}" style="height: 145px; object-fit: contain;"
                     onerror="this.src='/static/img/Data/%E8%99%9B%E5%BC%B1%E5%85%94.png'">
                <div class="card-body text-center">
                    <h6 class="card-title">${creature.name || '未知精靈'}</h6>
                    <span class="badge bg-secondary">${element}</span>
                    <div class="mt-2">
                        <small class="text-muted">ATK: ${creature.attack || creature.power || 100} | HP: ${creature.hp || 1000}</small>
                    </div>
                </div>
            </div>
        `;

        div.querySelector('.creature-card').addEventListener('click', () => {
            this.selectCreature(creature, div.querySelector('.creature-card'));
        });
        return div;
    }

    selectCreature(creature, card) {
        this.selectedCreatureId = creature.id;
        this.selectedCreature = creature;

        document.querySelectorAll('.creature-card').forEach(item => item.classList.remove('selected'));
        card.classList.add('selected');

        this.renderCreature('player-slot', creature);
        document.getElementById('match-button').style.display = 'inline-block';

        const modal = bootstrap.Modal.getInstance(document.getElementById('spriteModal'));
        if (modal) {
            modal.hide();
        }
    }

    renderCreature(slotId, creature, label = '') {
        const imageUrl = creature.image_url || '/static/img/Data/%E8%99%9B%E5%BC%B1%E5%85%94.png';
        const element = creature.element || creature.type || creature.element_type || 'normal';
        document.getElementById(slotId).innerHTML = `
            <img src="${imageUrl}" alt="${creature.name}" onerror="this.src='/static/img/Data/%E8%99%9B%E5%BC%B1%E5%85%94.png'">
            <div class="mt-2 text-center"><strong>${creature.name || '未知精靈'}</strong></div>
            ${label ? `<div class="small text-muted text-center">${label}</div>` : ''}
            <small class="text-muted">ATK: ${creature.attack || creature.power || 100} | HP: ${creature.hp || 1000} | ${element}</small>
        `;
    }

    startMatch() {
        if (!this.selectedCreatureId) {
            this.showStatus('請先選擇出戰精靈', 'warning');
            return;
        }

        this.setButtonLoading(true, '取得定位中...');
        this.getLocation()
            .then(location => {
                this.location = location;
                this.showStatus('正在搜尋附近玩家', 'info');
                return this.requestMatch(false);
            })
            .then(data => this.handleMatchResponse(data))
            .catch(error => {
                console.warn('定位或搜尋失敗:', error);
                this.showStatus('無法取得定位', 'warning');
                this.requestMatch(true).then(data => this.handleMatchResponse(data));
            });
    }

    getLocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error('geolocation unavailable'));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                position => resolve({
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                }),
                reject,
                {
                    enableHighAccuracy: true,
                    timeout: 5000,
                    maximumAge: 10000
                }
            );
        });
    }

    requestMatch(forceCpu) {
        return fetch(this.urls.match, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                creature_id: this.selectedCreatureId,
                lat: this.location && this.location.lat,
                lng: this.location && this.location.lng,
                match_token: this.matchToken,
                force_cpu: forceCpu
            })
        }).then(response => response.json());
    }

    handleMatchResponse(data) {
        if (!data.success) {
            this.showStatus(data.message || '搜尋對手失敗', 'danger');
            this.setButtonLoading(false);
            return;
        }

        if (data.status === 'matched') {
            this.finishBattle(data.battle_result);
            return;
        }

        this.matchToken = data.match_token;
        this.startWaitingTimers();
    }

    startWaitingTimers() {
        this.setButtonLoading(true, '搜尋中...');

        this.statusTimer = setInterval(() => {
            fetch(this.urls.status.replace('MATCH_TOKEN', this.matchToken))
                .then(response => response.json())
                .then(data => {
                    if (data.success && data.status === 'matched') {
                        this.clearTimers();
                        this.finishBattle(data.battle_result);
                    }
                })
                .catch(error => console.warn('查詢路人配對狀態失敗:', error));
        }, 1000);

        this.fallbackTimer = setTimeout(() => {
            this.clearTimers();
            this.showStatus('5 秒內沒有找到附近玩家，正在配對電腦對手...', 'warning');
            this.requestMatch(true).then(data => this.handleMatchResponse(data));
        }, 5000);
    }

    finishBattle(result) {
        this.clearTimers();
        this.setButtonLoading(false);
        document.getElementById('match-button').style.display = 'none';
        document.getElementById('result-actions').style.display = 'none';

        this.renderCreature('player-slot', result.player_creature);
        this.renderCreature('opponent-slot', result.opponent_creature, result.opponent_name || '附近對手');

        document.getElementById('player-slot').classList.remove('winner-glow', 'loser-fade');
        document.getElementById('opponent-slot').classList.remove('winner-glow', 'loser-fade');
        this.showStatus(`找到對手：${result.opponent_name || '附近對手'}！戰鬥開始...`, 'primary');

        this.sleep(1000)
            .then(() => this.runClashAnimation())
            .then(() => this.showFinalResult(result));
    }

    sleep(ms) {
        return new Promise(resolve => {
            setTimeout(resolve, ms);
        });
    }

    async runClashAnimation() {
        const playerSlot = document.getElementById('player-slot');
        const opponentSlot = document.getElementById('opponent-slot');

        for (let i = 0; i < 3; i++) {
            await new Promise(resolve => {
                playerSlot.classList.remove('clash-from-left');
                opponentSlot.classList.remove('clash-from-right');
                void playerSlot.offsetWidth;

                playerSlot.classList.add('clash-from-left');
                opponentSlot.classList.add('clash-from-right');

                setTimeout(() => {
                    playerSlot.classList.remove('clash-from-left');
                    opponentSlot.classList.remove('clash-from-right');
                    resolve();
                }, 650);
            });

            if (i < 2) {
                await this.sleep(500);
            }
        }
    }

    showFinalResult(result) {
        document.getElementById('result-actions').style.display = 'block';

        if (result.winner === 'draw') {
            this.showStatus('平手！這場對戰勢均力敵。', 'info');
            return;
        }

        const playerWon = result.winner === 'player';
        if (playerWon) {
            document.getElementById('player-slot').classList.add('winner-glow');
            document.getElementById('opponent-slot').classList.add('loser-fade');
            this.showStatus(`獲勝！你的 ${result.winner_name} 擊敗了 ${result.opponent_name || '對手'} 的 ${result.loser_name}。`, 'success');
        } else {
            document.getElementById('opponent-slot').classList.add('winner-glow');
            document.getElementById('player-slot').classList.add('loser-fade');
            this.showStatus(`落敗！${result.opponent_name || '對手'} 的 ${result.winner_name} 擊敗了你的 ${result.loser_name}。`, 'danger');
        }
    }

    clearTimers() {
        if (this.statusTimer) {
            clearInterval(this.statusTimer);
            this.statusTimer = null;
        }
        if (this.fallbackTimer) {
            clearTimeout(this.fallbackTimer);
            this.fallbackTimer = null;
        }
    }

    setButtonLoading(isLoading, text = '開始搜尋附近對手') {
        const button = document.getElementById('match-button');
        button.disabled = isLoading;
        button.innerHTML = isLoading
            ? `<i class="fas fa-spinner fa-spin me-2"></i>${text}`
            : '<i class="fas fa-location-crosshairs me-2"></i>開始搜尋附近對手';
    }

    showStatus(message, type) {
        const statusDiv = document.getElementById('status-message');
        const statusText = document.getElementById('status-text');
        statusDiv.className = `alert alert-${type} mt-3`;
        statusDiv.style.display = 'block';
        statusText.textContent = message;
    }
}

let passerbyFight = null;

document.addEventListener('DOMContentLoaded', () => {
    if (typeof passerbyFightConfig !== 'undefined') {
        passerbyFight = new PasserbyFight(passerbyFightConfig);
        passerbyFight.init();
    }
});
