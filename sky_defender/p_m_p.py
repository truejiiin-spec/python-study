# 플레이어
PLAYER_SPEED = 5                  # 초당 300px
PLAYER_BOTTOM_MARGIN = 10         # 시작 위치: 화면 하단에서 띄울 거리
SHOT_DELAY_MS = 100               # 발사 간격(ms). 작을수록 연사가 빨라짐

# =====================================================================
# 4. 스프라이트
#    - pygame.sprite.Sprite 를 상속하면 image/rect 만 준비해도
#      Group.update() / Group.draw() / 충돌 함수를 그대로 쓸 수 있다.
#    - Sprite.__init__(*groups) 에 그룹을 넘기면 생성과 동시에 그룹에 등록된다.
# =====================================================================
class Player(pygame.sprite.Sprite):
    """아군 비행기: 키 입력으로 이동/발사"""

    def __init__(self, image: pygame.Surface):
        super().__init__()
        self.image = image
        # mask: 투명 부분을 제외한 실제 모양 → 충돌 판정을 사각형보다 정확하게
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.speed = PLAYER_SPEED
        self.screen_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.reset_position()

    def reset_position(self) -> None:
        """화면 하단 중앙으로 이동 (게임 시작/라운드 리셋 시 사용)"""
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - PLAYER_BOTTOM_MARGIN

    def update(self) -> None:
        keys = pygame.key.get_pressed()

        # True/False 는 1/0 으로 계산된다 → (오른쪽 - 왼쪽) = -1, 0, 1
        # if/elif 로 처리하면 한 번에 한 방향만 되지만, 합산하면 대각선 이동이 가능
        self.rect.x += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * self.speed
        self.rect.y += (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * self.speed

        # clamp_ip: rect 를 지정 영역 안으로 밀어 넣음 (상하좌우 경계 체크를 한 줄로)
        self.rect.clamp_ip(self.screen_rect)

# `Game.__init__` 에서 배경 로드 아래에 추가한다.

        player_img = load_image(PLAYER_FILE, fallback_color=(80, 160, 255))

        # ── 스프라이트 그룹 ──
        # all_sprites : 업데이트/그리기용 전체 묶음
        self.all_sprites = pygame.sprite.Group()

        self.player = Player(player_img)
        self.all_sprites.add(self.player)

# `update()` 와 `draw()` 에 한 줄씩 추가한다.

        def update(self) -> None:
            self.background.update()          # 게임오버 화면에서도 배경은 계속 흐르게

            # 모든 스프라이트의 update() 를 호출 - 반드시 프레임당 1회
            # (2번 호출하면 모든 객체가 2배 속도로 움직인다)
            self.all_sprites.update()

        def draw(self) -> None:
            self.background.draw(self.screen)
            self.all_sprites.draw(self.screen)
        

            # 메모리에 그린 화면을 실제 모니터에 한 번에 반영 (더블 버퍼링 → 깜빡임 방지)
            pygame.display.flip()