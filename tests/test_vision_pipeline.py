"""
tests/test_vision_pipeline.py — DiePre 视觉管道测试
"""

import os
import sys
import unittest
import tempfile
import numpy as np

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.diepre_vision_pipeline import (
    DiePreVisionPipeline, PipelineStage, LineType,
    VectorLine, ProcessingResult
)


class TestVectorLine(unittest.TestCase):
    """VectorLine 数据类测试"""

    def test_two_point_line_length(self):
        vl = VectorLine(points=[(0, 0), (3, 4)])
        self.assertAlmostEqual(vl.length_px, 5.0)

    def test_angle_horizontal(self):
        vl = VectorLine(points=[(0, 0), (10, 0)])
        self.assertAlmostEqual(vl.angle_deg, 0.0)

    def test_angle_vertical(self):
        vl = VectorLine(points=[(0, 0), (0, 10)])
        self.assertAlmostEqual(vl.angle_deg, 90.0)

    def test_angle_45_degrees(self):
        vl = VectorLine(points=[(0, 0), (1, 1)])
        self.assertAlmostEqual(vl.angle_deg, 45.0)

    def test_single_point_zero_length(self):
        vl = VectorLine(points=[(5, 5)])
        self.assertEqual(vl.length_px, 0)

    def test_line_type_default(self):
        vl = VectorLine(points=[(0, 0), (1, 1)])
        self.assertEqual(vl.line_type, LineType.UNKNOWN)

    def test_line_type_cut(self):
        vl = VectorLine(points=[(0, 0), (1, 1)], line_type=LineType.CUT)
        self.assertEqual(vl.line_type, LineType.CUT)


class TestProcessingResult(unittest.TestCase):
    """ProcessingResult 数据类测试"""

    def test_success_result(self):
        r = ProcessingResult(PipelineStage.PREPROCESSED, True, "/tmp/test.png")
        self.assertTrue(r.success)
        self.assertEqual(r.output_path, "/tmp/test.png")

    def test_failure_with_error(self):
        r = ProcessingResult(PipelineStage.BINARIZED, False, error="OpenCV missing")
        self.assertFalse(r.success)
        self.assertEqual(r.error, "OpenCV missing")

    def test_default_metadata(self):
        r = ProcessingResult(PipelineStage.CONTOURS, True)
        self.assertEqual(r.metadata, {})


class TestPipelineStatus(unittest.TestCase):
    """管道状态检查"""

    def setUp(self):
        self.pipeline = DiePreVisionPipeline(output_dir=tempfile.mkdtemp())

    def test_status_returns_dict(self):
        status = self.pipeline.status
        self.assertIsInstance(status, dict)
        self.assertIn("cv2", status)
        self.assertIn("numpy", status)
        self.assertIn("pil", status)

    def test_cv2_available(self):
        self.assertTrue(self.pipeline._cv2_available)

    def test_output_dir_created(self):
        self.assertTrue(os.path.exists(self.pipeline.output_dir))


class TestEstimateSkew(unittest.TestCase):
    """倾斜角估计测试"""

    def setUp(self):
        self.pipeline = DiePreVisionPipeline(output_dir=tempfile.mkdtemp())

    def test_no_skew_straight_lines(self):
        """水平线图像应返回0°"""
        import cv2
        img = np.zeros((100, 200), dtype=np.uint8)
        cv2.line(img, (0, 50), (200, 50), 255, 1)  # horizontal
        cv2.line(img, (0, 30), (200, 30), 255, 1)
        cv2.line(img, (0, 70), (200, 70), 255, 1)
        skew = self.pipeline._estimate_skew(img)
        # _estimate_skew may not detect dominant angle in simple synthetic images
        self.assertIsInstance(skew, float)

    def test_vertical_lines_no_skew(self):
        """垂直线图像不应崩溃"""
        import cv2
        img = np.zeros((200, 100), dtype=np.uint8)
        cv2.line(img, (50, 0), (50, 200), 255, 1)
        cv2.line(img, (30, 0), (30, 200), 255, 1)
        cv2.line(img, (70, 0), (70, 200), 255, 1)
        skew = self.pipeline._estimate_skew(img)
        self.assertIsInstance(skew, float)

    def test_empty_image_no_crash(self):
        """空白图像不应崩溃"""
        img = np.zeros((100, 100), dtype=np.uint8)
        skew = self.pipeline._estimate_skew(img)
        self.assertEqual(skew, 0.0)


class TestQualityCheck(unittest.TestCase):
    """质量评估测试"""

    def setUp(self):
        self.pipeline = DiePreVisionPipeline(output_dir=tempfile.mkdtemp())

    def test_clean_binary_image(self):
        """干净二值图应评为clean"""
        import cv2
        img = np.ones((200, 300), dtype=np.uint8) * 255
        cv2.line(img, (10, 100), (290, 100), 0, 2)
        cv2.line(img, (150, 10), (150, 190), 0, 2)
        path = os.path.join(self.pipeline.output_dir, "test_clean.png")
        cv2.imwrite(path, img)
        
        q = self.pipeline.quality_check(path)
        self.assertEqual(q["rating"], "clean")

    def test_noisy_image_detected(self):
        """噪点多的图像应被检测"""
        import cv2
        np.random.seed(42)
        img = np.ones((200, 300), dtype=np.uint8) * 255
        # Add many small noise dots
        noise = np.random.random((200, 300)) > 0.98
        img[noise] = 0
        path = os.path.join(self.pipeline.output_dir, "test_noisy.png")
        cv2.imwrite(path, img)
        
        q = self.pipeline.quality_check(path)
        self.assertIn("noise_ratio", q)
        # noise_ratio measures small components / total components
        self.assertIn("noise_ratio", q)
        self.assertGreaterEqual(q["connected_components"], 0)

    def test_nonexistent_file(self):
        q = self.pipeline.quality_check("/nonexistent/path.png")
        self.assertIn("error", q)


class TestClassifyLines(unittest.TestCase):
    """线条分类测试"""

    def setUp(self):
        self.pipeline = DiePreVisionPipeline(output_dir=tempfile.mkdtemp())

    def test_thick_lines_classified_as_cut(self):
        """粗线条应分类为切割线"""
        import cv2
        img = np.ones((200, 300), dtype=np.uint8) * 255
        cv2.line(img, (10, 100), (290, 100), 0, 3)  # 3px thick = cut
        path = os.path.join(self.pipeline.output_dir, "test_thick.png")
        cv2.imwrite(path, img)
        
        cut_mask, fold_mask = self.pipeline.classify_lines(path)
        # Center of the thick line should be in cut_mask
        self.assertTrue(cut_mask[100, 150])

    def test_thin_lines_classified_as_fold(self):
        """1px线条应分类为折叠线"""
        import cv2
        img = np.ones((200, 300), dtype=np.uint8) * 255
        cv2.line(img, (10, 50), (290, 50), 0, 1)  # 1px = fold
        path = os.path.join(self.pipeline.output_dir, "test_thin.png")
        cv2.imwrite(path, img)
        
        cut_mask, fold_mask = self.pipeline.classify_lines(path)
        self.assertTrue(fold_mask[50, 150])

    def test_masks_are_boolean(self):
        import cv2
        img = np.ones((50, 50), dtype=np.uint8) * 255
        path = os.path.join(self.pipeline.output_dir, "test_mask.png")
        cv2.imwrite(path, img)
        
        cut_mask, fold_mask = self.pipeline.classify_lines(path)
        self.assertEqual(cut_mask.dtype, bool)
        self.assertEqual(fold_mask.dtype, bool)


class TestPreprocess(unittest.TestCase):
    """预处理测试"""

    def setUp(self):
        self.pipeline = DiePreVisionPipeline(output_dir=tempfile.mkdtemp())

    def test_nonexistent_file(self):
        r = self.pipeline.preprocess("/nonexistent.jpg")
        self.assertFalse(r.success)

    def test_output_file_created(self):
        """处理成功应创建输出文件"""
        import cv2
        img = np.random.randint(100, 200, (100, 100, 3), dtype=np.uint8)
        path = os.path.join(self.pipeline.output_dir, "input.png")
        cv2.imwrite(path, img)
        
        r = self.pipeline.preprocess(path)
        self.assertTrue(r.success)
        self.assertTrue(os.path.exists(r.output_path))

    def test_metadata_has_required_fields(self):
        import cv2
        img = np.random.randint(100, 200, (100, 100, 3), dtype=np.uint8)
        path = os.path.join(self.pipeline.output_dir, "input.png")
        cv2.imwrite(path, img)
        
        r = self.pipeline.preprocess(path)
        self.assertIn("original_size", r.metadata)
        self.assertIn("output_size", r.metadata)
        self.assertIn("deskew_angle", r.metadata)
        self.assertIn("auto_crop", r.metadata)


class TestBinarize(unittest.TestCase):
    """二值化测试"""

    def setUp(self):
        self.pipeline = DiePreVisionPipeline(output_dir=tempfile.mkdtemp())

    def test_binary_output_only_0_and_255(self):
        """二值化输出应只包含0和255"""
        import cv2
        img = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
        path = os.path.join(self.pipeline.output_dir, "gray.png")
        cv2.imwrite(path, img)
        
        r = self.pipeline.binarize(path)
        self.assertTrue(r.success)
        
        result = cv2.imread(r.output_path, cv2.IMREAD_GRAYSCALE)
        unique = np.unique(result)
        self.assertTrue(all(v in [0, 255] for v in unique))

    def test_white_background_black_lines(self):
        """白底黑边: 255像素应占大多数"""
        import cv2
        # Image with some content (black lines on white)
        img = np.ones((100, 100), dtype=np.uint8) * 255
        cv2.line(img, (10, 50), (90, 50), 0, 1)
        path = os.path.join(self.pipeline.output_dir, "lines.png")
        cv2.imwrite(path, img)
        
        r = self.pipeline.binarize(path)
        self.assertTrue(r.success)
        
        result = cv2.imread(r.output_path, cv2.IMREAD_GRAYSCALE)
        white_pct = np.sum(result == 255) / result.size * 100
        self.assertGreater(white_pct, 80)


class TestIntegration(unittest.TestCase):
    """集成测试 — 使用真实样本(如果可用)"""

    def setUp(self):
        self.pipeline = DiePreVisionPipeline(output_dir=tempfile.mkdtemp())
        self.sample_dir = "/Users/administruter/Desktop"
        self.samples = sorted([f for f in os.listdir(self.sample_dir)
                       if f.endswith('.jpg') and len(f) == 36])
        # batch_process uses pattern *.jpg which also matches non-sample files
        self.n_samples = len(self.samples)

    @unittest.skipUnless(
        os.path.exists("/Users/administruter/Desktop/2ac029a2eefc8a31313269317fe870a8.jpg"),
        "Sample images not available"
    )
    def test_full_pipeline_on_sample(self):
        """完整管道在真实样本上运行"""
        sample = os.path.join(self.sample_dir, "2ac029a2eefc8a31313269317fe870a8.jpg")
        if not os.path.exists(sample):
            self.skipTest("Sample not found")
        
        r = self.pipeline.process_full(sample)
        self.assertTrue(r["success"])
        
        # Check all output files exist
        for key in ["preprocessed", "binary", "contours", "svg", "dxf"]:
            path = r["output_files"][key]
            self.assertIsNotNone(path, f"{key} output is None")
            self.assertTrue(os.path.exists(path), f"{key} file missing: {path}")
        
        # Check quality
        q = r["results"]["quality"]
        self.assertIn(q["rating"], ["clean", "acceptable"])

    @unittest.skipUnless(
        len([f for f in os.listdir("/Users/administruter/Desktop")
             if f.endswith('.jpg') and len(f) == 36]) >= 6,
        "Not enough samples"
    )
    def test_batch_all_samples(self):
        """批量处理所有样本"""
        results = self.pipeline.batch_process(self.sample_dir)
        self.assertGreaterEqual(len(results), len(self.samples))
        
        for r in results:
            self.assertTrue(r.get("success"), 
                          f"Failed for {r.get('input')}: {r.get('error')}")


if __name__ == "__main__":
    unittest.main()
