"""
thumbnail.py에 대한 단위 테스트

테스트 범위:
- convert_to_images: PowerPoint를 이미지로 변환
- create_grids: 썸네일 그리드 생성
- create_grid: 단일 그리드 생성
- get_placeholder_regions: 플레이스홀더 영역 추출
- create_hidden_slide_placeholder: 숨겨진 슬라이드 플레이스홀더 생성
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# 테스트 대상 모듈 import
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from thumbnail import (
    convert_to_images,
    create_grid,
    create_grids,
    create_hidden_slide_placeholder,
    get_placeholder_regions,
)


class TestCreateHiddenSlidePlaceholder:
    """숨겨진 슬라이드 플레이스홀더 생성 테스트"""

    @patch("thumbnail.ImageDraw")
    @patch("thumbnail.Image")
    def test_create_placeholder_basic(self, mock_image_class, mock_imagedraw):
        """정상 케이스: 기본 플레이스홀더 생성"""
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.new.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        result = create_hidden_slide_placeholder((800, 600))

        # 검증
        mock_image_class.new.assert_called_once_with("RGB", (800, 600), color="#F0F0F0")
        assert mock_draw.line.call_count == 2  # X자 두 선

    @patch("thumbnail.ImageDraw")
    @patch("thumbnail.Image")
    def test_create_placeholder_different_sizes(self, mock_image_class, mock_imagedraw):
        """정상 케이스: 다양한 크기"""
        mock_img = MagicMock()
        mock_draw = MagicMock()
        mock_image_class.new.return_value = mock_img
        mock_imagedraw.Draw.return_value = mock_draw

        # 작은 크기
        create_hidden_slide_placeholder((100, 100))
        mock_image_class.new.assert_called_with("RGB", (100, 100), color="#F0F0F0")

        # 큰 크기
        create_hidden_slide_placeholder((1920, 1080))
        mock_image_class.new.assert_called_with("RGB", (1920, 1080), color="#F0F0F0")


class TestGetPlaceholderRegions:
    """플레이스홀더 영역 추출 테스트"""

    @patch("thumbnail.Presentation")
    @patch("thumbnail.extract_text_inventory")
    def test_get_placeholder_regions_basic(self, mock_inventory, mock_prs_class):
        """정상 케이스: 플레이스홀더 영역 추출"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_prs.slide_width = 9144000  # EMU
        mock_prs.slide_height = 6858000  # EMU
        mock_prs_class.return_value = mock_prs

        # Mock inventory
        mock_inventory.return_value = {
            "slide-0": {
                "shape-0": MagicMock(
                    left=1.0, top=1.0, width=2.0, height=1.0
                )
            },
            "slide-1": {
                "shape-0": MagicMock(
                    left=0.5, top=0.5, width=3.0, height=2.0
                )
            },
        }

        # 각 shape에 대해 속성 딕셔너리 반환
        for slide_shapes in mock_inventory.return_value.values():
            for shape in slide_shapes.values():
                type(shape).left = property(lambda self: self._left)
                type(shape).top = property(lambda self: self._top)
                type(shape).width = property(lambda self: self._width)
                type(shape).height = property(lambda self: self._height)
                shape._left = shape.left if hasattr(shape, '_left') else 1.0
                shape._top = shape.top if hasattr(shape, '_top') else 1.0
                shape._width = shape.width if hasattr(shape, '_width') else 2.0
                shape._height = shape.height if hasattr(shape, '_height') else 1.0

        regions, dimensions = get_placeholder_regions(Path("test.pptx"))

        # 검증
        assert dimensions is not None
        assert regions is not None

    @patch("thumbnail.Presentation")
    @patch("thumbnail.extract_text_inventory")
    def test_get_placeholder_regions_no_text(self, mock_inventory, mock_prs_class):
        """정상 케이스: 텍스트가 없는 경우"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_prs.slide_width = 9144000
        mock_prs.slide_height = 6858000
        mock_prs_class.return_value = mock_prs

        # Mock inventory (빈 인벤토리)
        mock_inventory.return_value = {}

        regions, dimensions = get_placeholder_regions(Path("test.pptx"))

        # 검증
        assert regions == {}
        assert dimensions is not None


class TestConvertToImages:
    """PowerPoint 이미지 변환 테스트"""

    @patch("thumbnail.subprocess.run")
    @patch("thumbnail.Presentation")
    @patch("thumbnail.Image")
    def test_convert_to_images_no_hidden_slides(self, mock_image_class, mock_prs_class, mock_subprocess):
        """정상 케이스: 숨겨진 슬라이드가 없는 경우"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_slide1 = MagicMock()
        mock_slide1.element.get.return_value = None  # 숨김 아님
        mock_slide2 = MagicMock()
        mock_slide2.element.get.return_value = None
        mock_prs.slides = [mock_slide1, mock_slide2]
        mock_prs_class.return_value = mock_prs

        # Mock subprocess (성공)
        mock_subprocess.return_value.returncode = 0

        # Mock temp directory에 생성된 이미지 파일
        with patch("thumbnail.Path") as mock_path_class:
            mock_temp_dir = MagicMock()

            # Create mock Path objects that can be sorted by using __lt__ magic method
            mock_slide_path1 = MagicMock(spec=Path)
            mock_slide_path1.__lt__ = MagicMock(return_value=True)
            mock_slide_path1.__str__ = MagicMock(return_value="slide-1.jpg")
            mock_slide_path2 = MagicMock(spec=Path)
            mock_slide_path2.__lt__ = MagicMock(return_value=False)
            mock_slide_path2.__str__ = MagicMock(return_value="slide-2.jpg")

            # Return an iterator that can be sorted
            mock_temp_dir.glob.return_value = iter([mock_slide_path1, mock_slide_path2])

            # pdf_path.exists() True 반환
            mock_pdf = MagicMock()
            mock_pdf.exists.return_value = True
            mock_temp_dir.__truediv__.return_value = mock_pdf

            result = convert_to_images(Path("test.pptx"), mock_temp_dir, dpi=100)

            # 검증
            assert len(result) == 2

    @patch("thumbnail.subprocess.run")
    @patch("thumbnail.Presentation")
    @patch("thumbnail.Image")
    def test_convert_to_images_with_hidden_slides(
        self, mock_image_class, mock_prs_class, mock_subprocess
    ):
        """정상 케이스: 숨겨진 슬라이드가 있는 경우"""
        # Mock presentation
        mock_prs = MagicMock()
        mock_slide1 = MagicMock()
        mock_slide1.element.get.return_value = None
        mock_slide2 = MagicMock()
        mock_slide2.element.get.return_value = "0"  # 숨김
        mock_slide3 = MagicMock()
        mock_slide3.element.get.return_value = None
        mock_prs.slides = [mock_slide1, mock_slide2, mock_slide3]
        mock_prs_class.return_value = mock_prs

        # Mock subprocess
        mock_subprocess.return_value.returncode = 0

        # Mock 이미지 파일 (숨김 제외 2개)
        with patch("thumbnail.Path") as mock_path_class:
            mock_temp_dir = MagicMock()
            mock_img1 = MagicMock()
            mock_img2 = MagicMock()
            mock_img1.__enter__ = MagicMock(return_value=MagicMock(size=(800, 600)))
            mock_img2.__enter__ = MagicMock(return_value=MagicMock(size=(800, 600)))

            mock_visible_images = [
                Path("/tmp/slide-1.jpg"),
                Path("/tmp/slide-3.jpg"),
            ]
            mock_temp_dir.glob.return_value = mock_visible_images

            mock_pdf = MagicMock()
            mock_pdf.exists.return_value = True
            mock_temp_dir.__truediv__ = lambda self, x: mock_pdf if 'pdf' in str(x) else Path(f"/tmp/{x}")

            # Mock Image.open
            mock_image_class.open.side_effect = [mock_img1, mock_img2]

            result = convert_to_images(Path("test.pptx"), mock_temp_dir, dpi=100)

            # 검증: 3개 슬라이드 (1개는 플레이스홀더)
            assert len(result) == 3


class TestCreateGrid:
    """단일 그리드 생성 테스트"""

    @patch("thumbnail.ImageDraw")
    @patch("thumbnail.ImageFont")
    @patch("thumbnail.Image")
    def test_create_grid_basic(self, mock_image_class, mock_font, mock_imagedraw):
        """정상 케이스: 기본 그리드 생성"""
        # Mock 이미지 파일
        mock_img = MagicMock()
        mock_img.size = (800, 600)
        mock_img.height = 600
        mock_img.width = 800
        mock_image_class.open.return_value.__enter__.return_value = mock_img
        mock_img.thumbnail = MagicMock()

        # Mock new image
        mock_grid = MagicMock()
        mock_image_class.new.return_value = mock_grid

        # Mock ImageDraw
        mock_draw = MagicMock()
        mock_imagedraw.Draw.return_value = mock_draw
        mock_draw.textbbox.return_value = (0, 0, 20, 15)

        # Mock font
        mock_font.load_default.return_value = MagicMock()

        image_paths = [Path("/tmp/slide-1.jpg"), Path("/tmp/slide-2.jpg")]
        result = create_grid(image_paths, cols=2, width=300)

        # 검증
        mock_image_class.new.assert_called_once()
        assert result == mock_grid


class TestCreateGrids:
    """그리드 생성 테스트"""

    @patch("thumbnail.create_grid")
    def test_create_grids_single_grid(self, mock_create_grid):
        """정상 케이스: 단일 그리드 생성"""
        # Mock create_grid
        mock_grid = MagicMock()
        mock_create_grid.return_value = mock_grid

        # 5개 슬라이드, 5열 (최대 30개까지 한 그리드)
        image_paths = [Path(f"/tmp/slide-{i}.jpg") for i in range(5)]
        output_path = Path("/tmp/output.jpg")

        result = create_grids(image_paths, 5, 300, output_path)

        # 검증: 1개 그리드 파일만 생성
        assert len(result) == 1
        assert result[0] == str(output_path)
        mock_grid.save.assert_called_once()

    @patch("thumbnail.create_grid")
    def test_create_grids_multiple_grids(self, mock_create_grid):
        """정상 케이스: 여러 그리드 생성"""
        # Mock create_grid
        mock_grid = MagicMock()
        mock_create_grid.return_value = mock_grid

        # 40개 슬라이드, 5열 (최대 30개씩 → 2개 그리드)
        image_paths = [Path(f"/tmp/slide-{i}.jpg") for i in range(40)]
        output_path = Path("/tmp/output.jpg")

        result = create_grids(image_paths, 5, 300, output_path)

        # 검증: 2개 그리드 파일 생성
        assert len(result) == 2
        assert "/tmp/output-1.jpg" in result[0]
        assert "/tmp/output-2.jpg" in result[1]

    @patch("thumbnail.create_grid")
    def test_create_grids_exact_limit(self, mock_create_grid):
        """경계 케이스: 정확히 최대 개수"""
        # Mock create_grid
        mock_grid = MagicMock()
        mock_create_grid.return_value = mock_grid

        # 30개 슬라이드, 5열 (정확히 5×6=30)
        image_paths = [Path(f"/tmp/slide-{i}.jpg") for i in range(30)]
        output_path = Path("/tmp/output.jpg")

        result = create_grids(image_paths, 5, 300, output_path)

        # 검증: 1개 그리드만 생성
        assert len(result) == 1
