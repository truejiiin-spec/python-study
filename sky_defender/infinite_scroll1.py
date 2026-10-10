""" 
종스크롤 디펜더 슈팅 게임 (pygame 2.x)

[게임 규칙]
  - 방향키: 이동 / space: 발사 / R: 게임오버 후 재시작 / ESC: 종료
  - 적이 화면 하단을 통과하거나 아군과 부딪히면 목숨 -1, 라운드 리셋
  - 목숨 3개를 모두 잃으면 게임 오버

[코드 구조]
  1. 설정값      : 난이도·크기·색 등 "솟자"를 한곳에 모아 조절하기 쉽게 함
  2. 에셋 로더    : 파일 경로/로딩 실패 처리를 한곳에서 담당
  3. 배경        : 이음새 없는 이미지를 무한 스크롤
  4. 스프라이트   : Bullet / Player / Enemy - 각자 "자기 움직임"만 책임짐
  5. Game 클래스  : 이벤트 → 업데이트 → 그리기 순서의 게임 루프와 규칙(점수·목숨) 딤딩

[필요 파일] (이 파일과 같은 풀더)
  classic_bg_800x1400_seamless.png, shooter1.png, enemy1.png, NanumGothic.ttf
  ※ 파일이 없어도 대체 도형/기본 폰트로 실행은 됨 (에셋 로더 참고)   
"""
import os
import random
import sys

import pygame

# ======================================================================================
# 1. 설정값
#    - 코드 곳곳에 숫자를 직접 쓰면(매직 넘버) 난이도 조절 시 찾기 어렵다.
#    - 대문자 상수로 모아두면 "밸런스 조절 = 이 블록만 수정"이 된다. 
#    - 속도 단위는 px/frame 이다. FPS를 60으로 고정하므로 초당 이동량 = 값 x 60
# =======================================================================================
SCREEN_WIDTH, SCREEN_HEIGHT = 1376, 1000
FPS = 60
TITLE = "Sky Defender"

SCROLL_SPEED = 9

# 에셋 파일명
BG_FILE = "bg_down.png"
PLAYER_FILE = "neon.png"

TARGET_SIZE_RATIO = 0.5

CELL_FILE = "player_down.png"


ENEMY_FILE = "enemy1.png"
EXPLOSION_FILE = "explosion.png"
FONT_FILE = "NanumGothic.ttf"

# 플레이어
PLAYER_SPEED = 5            # 초당 300px
PLAYER_BOTTOM_MARGIN = 450   # 시작 위치: 화면 하단에서 띄울 거리
SHOT_DELAY_MS = 100         # 발사 간격(ms). 작을수록 연사가 빨라짐
CELL_BOTTOM = 990


#색 (R, G, B)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
ORANGE = (255, 165, 0)
YELLOW = (255, 255, 0)
BULLET_CORE = (255, 240, 150)

# =======================================================================================
# 2. 에셋 로더
# =======================================================================================
# 이 .py 파일이 있는 풀더를 기준으로 경로를 만든다.
#  - sys.argv[0]은 IDE 실행/모듈 import 시 빈 문자열이 될 수 있어 불안정하다.
#  -  __file__ 은 항상 "현재 소스 파일" 경로이므로 반드시 어디서 실행해도 같은 결과가 나온다.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename: str) -> str:
    """에셋 파일의 절대 경로를 반환 (실행 위치와 무관하게 동일)"""
    return os.path.join(BASE_DIR, filename)


def load_image(filename: str, alpha: bool = True,
               fallback_size = (40, 40), fallback_color = WHITE,
               pointing_up: bool = True, fallback_shape: str = "triangle") -> pygame.Surface:
    """ 
    이미지를 불러와 화면 픽셀 포맷으로 변환해 반환한다.

    - convert()         : 불투명 이미지(배경)용. blit 속도가 수 배 빨라진다.
    - convert_alphe()   : 투명 영역이 있는 이미지(비행기)용.
    - 파일이 없으면 삼각형 대체 이미지를 만들어 게임이 멈추지 않게 한다.
      (수업 중 파일 누락으로 실습이 중단되는 상황 방지)

    ※ convert 계열은 display.set_mode() 이후에만 호출할 수 있다.   
    """
    path = asset_path(filename)
    try:
        image = pygame.image.load(path)
    except (FileNotFoundError, pygame.error):
        print(f"[경고] 이미지 파일 없음: {path} → 대체 도형 사용")
        w, h = fallback_size
        image = pygame.Surface((w, h), pygame.SRCALPHA)
        if fallback_shape == "circle":
            pygame.draw.circle(image, fallback_color, (w // 2, h // 2), min(w, h) // 2)
        else:
            points = [(w // 2, 0), (0, h), (w, h)] if pointing_up else [(0, 0), (w, 0), (w // 2, h)]
            pygame.draw.polygon(image, fallback_color, points)
    return image.convert_alpha() if alpha else image.convert()


def load_font(size: int) -> pygame.font.Font:
    """한글 폰트를 불러오고, 없으면 pygame 기본 폰트로 대체 (한글은 꺠질 수 있음)"""
    try:
        return pygame.font.Font(asset_path(FONT_FILE), size)
    except (FileNotFoundError, OSError): 
        print(f"[경고] 폰트 파일 없음: {asset_path(FONT_FILE)} → 기본 폰트 사용")
        return pygame.font.Font(None, size)

# ==========================================================================================
# 3. 배경 - 이음새 없는 이미지 무한 스크롤
# ==========================================================================================
class ScrollingBackground:
    """
    [원리]
      위아래가 이어지는 이미지는 "이미지 top 위에 같은 이미지가 또 붙어 있을 때"
      경계가 보이지 않는다. 그래서 위치(offset)를 이미지 높이로 나눈 나머지로 
      순환시키고, 원본 위쪽에 복사본을 이어 그린다. 

          ┌────────┐ ← offset - 높이   (복사본)
          │ 화면    │
          │────────│ ← offset          (원본)
          └────────┘

      기존 방식처럼 끝에서 "처음 위치로 순간이동"시키면 보이는 영역이
      한 번에 바뀌어 끊겨 보인다.     
    """

    def __init__(self, image: pygame.Surface, screen_height: int, speed: float):
        self.image = image
        self.height = image.get_height()
        self.screen_height = screen_height
        self.speed = speed
        self.offset = 0.0
        self.reset()

    def reset(self) -> None:
        """이미지 아랫부분이 화면에 보이는 위치에서 시작 (0 <= offset < 높이 로 정규화)"""
        self.offset = -(self.height - self.screen_height) % self.height

    def update(self) -> None:
        # 모듈로(%) 연산 → 값이 계속 커지지 않고 항상 [0, 높이] 범위에서 순환
        self.offset = (self.offset - self.speed) % self.height

    def draw(self, surface: pygame.Surface) -> None:
        # 한 장 위(복사본)부터 화면 아래 끝까지 필요한 만큼 이어 그린다.
        # 화면이 이미지보다 높아져도 빈틈이 생기지 않도록 while 사용
        y = int(self.offset) - self.height
        while y < self.screen_height:
            surface.blit(self.image, (0, y))
            y += self.height

# ============================================================================================
# 4. 스프라이트
#    - pygame.sprite.Sprite 를 상속하면 image/rect 만 준비해도
#      Group.update() / Group.draw() / 충돌 함수를 그대로 쓸 수 있다.
#    - Sprite.__init__(*groups) 에 그룹을 넘기면 생성과 동시에 그룹에 등록된다.
# ============================================================================================
class Player(pygame.sprite.Sprite):
    """아군 비행기: 키 입력으로 이동/발사"""

    def __init__(self, image: pygame.Surface):
        super().__init__()
        self.image = image
        # mask: 투명 부분을 제외한 실제 모양 → 충동 판정을 사각형보다 정확하게
        self.mask = pygame.mask.from_surface(self.image)
        self.rect = self.image.get_rect()
        self.speed = PLAYER_SPEED
        self.screen_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.reset_position()

    def reset_position(self) -> None:
        """화면 하단 중앙으로 이동 (게임 시잘/라운드 리셋 시 사용)"""
        self.rect.centerx = SCREEN_WIDTH // 2
        self.rect.bottom = SCREEN_HEIGHT - PLAYER_BOTTOM_MARGIN

    def update(self) -> None:
        keys = pygame.key.get_pressed()

        # True/False 는  1/0 으로 계산된다 → (오른쪽 - 왼쪽) = -1, 0, 1
        # if/elif 로 처리하면 한 번에 한 방향만 되지만, 합산하면 대각선 이동이 가능
        self.rect.x += (keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]) * self.speed
        self.rect.y += (keys[pygame.K_DOWN] - keys[pygame.K_UP]) * self.speed

        # clamp_ip: rect 를 지정 영역 안으로 밀어 넣음 (상하좌우 경계 체크를 한 줄로)  
        self.rect.clamp_ip(self.screen_rect)



    

# =============================================================================================
# 5. Game - 게임 루프와 규칙            
# =============================================================================================
class Game:
    """ 
    게임 루프의 기본 형태 (매 프레임 반복)

        handle_events()  : 입력/타이머 이벤트 처리
        update()         : 위치 이동, 충돌, 점수/목숨 계산 ← 한 프레임에 한 번만!
        draw()           : 화면 그리기

    상태(state)를 두어 "플레이 중"과 "게임 오버"의 동작을 분리한다.
    (if game_over: ... continue 방식보다 흐름이 명확하고 상태 추가가 쉬움)
    """

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)

        raw_player_img = load_image(PLAYER_FILE, fallback_color = (80, 160, 255), fallback_shape = "circle")

        new_w = int(raw_player_img.get_width() * TARGET_SIZE_RATIO)
        new_h = int(raw_player_img.get_height() * TARGET_SIZE_RATIO)

        scaled_player_file = pygame.transform.scale(raw_player_img, (new_w, new_h))


        # ㅡㅡ 스프라이트 그룹 ㅡㅡ
        # all_sprites : 업데이트/그리기용 전체 묶음
        self.all_sprites = pygame.sprite.Group()

        self.player = Player(scaled_player_file)
        self.person = load_image(CELL_FILE, fallback_color = (255, 255, 0))
        self.person_rect = self.person.get_rect(midbottom = (SCREEN_WIDTH // 2, CELL_BOTTOM))
        self.all_sprites.add(self.player)


        self.clock = pygame.time.Clock()
        self.background = ScrollingBackground(
            load_image(BG_FILE, alpha = False, fallback_size = (SCREEN_WIDTH, SCREEN_HEIGHT),
                       fallback_color = (40, 90, 50)),
            SCREEN_HEIGHT, SCROLL_SPEED)

        self.running = True

    # -----------------------------------------------------------------------------------------
    # 게임 루프
    # -----------------------------------------------------------------------------------------
    def run(self) -> None:
        while self.running:
            # tick() 은 직전 프레임 이후 흐른 시간(ms)을 반환 → 난이도용 시간 측정에 사용
            dt = self.clock.tick(FPS)   # 최대 60FPS 로 제한 (ps/frame 속도와 기준)
            self.handle_events()
            self.update()
            self.draw()
        pygame.quit()

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False    # 게임 루프를 빠져나오는 flag, false이면 종료(게임 루프 탈출)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self) -> None:
        self.background.update()        # 게임오버 화면에서도 배경은 계속 흐르게

        
        # 모든 스프라이트의 update() 를 호출 - 반드시 프레임당 1회
        # (2번 호출하면 모든 객체가 2배 속도로 움직인다)
        self.all_sprites.update()


    # ------------------------------------------------------------------------------------------
    # 그리기 (뒤에 있는 것부터: 배경 → 스프라이트 → UI)
    # ------------------------------------------------------------------------------------------
    def draw(self) -> None:
        self.screen.fill(BLACK)
        
        self.background.draw(self.screen)

        self.screen.blit(self.person, self.person_rect)
        self.all_sprites.draw(self.screen)

        # 메모리에 그린 화면을 실제 모니터에 한 번에 반영 (더블 버퍼링 → 깜빡임 방지)
        pygame.display.flip()

# ===============================================================================================
# 실행 진입점
#  - 이 파일을 직접 실행할 떄만 게임 시작
#  - 다른 파일에서 import 할 때는 실행되지 않음 (클래스 재사용/테스트 가능)
# ===============================================================================================
if __name__ == "__main__":
    Game().run()
    sys.exit()        
