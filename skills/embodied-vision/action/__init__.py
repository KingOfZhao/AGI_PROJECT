"""
embodied-vision/action — 动作视觉桥

从视觉感知到动作决策的桥梁:
- 视觉伺服 (Visual Servoing: 相机-目标对齐)
- 抓取规划 (Grasp Planning: 抓取点+方向+力度)
- 操作反馈 (Manipulation Monitor: 工具/物体交互监控)
- 运动轨迹规划 (基于视觉约束)
"""

import cv2
import numpy as np
from dataclasses import dataclass, field
from typing import List, Tuple, Dict, Optional
import math
import time


# ═══════════════════════════════════════════
# 数据结构
# ═══════════════════════════════════════════

@dataclass
class GraspPoint:
    """抓取点"""
    x: int; y: int  # 图像坐标
    approach_angle: float  # 接近角度(度, 0=从上方)
    width: float  # 抓取宽度(mm)
    quality: float  # 抓取质量评分 (0-1)
    method: str = "top"  # top/side/pinch
    depth: float = 0.0  # 抓取深度(mm)


@dataclass
class ServoCommand:
    """伺服命令"""
    dx: float; dy: float; dz: float  # 移动量(mm)
    droll: float; dpitch: float; dyaw: float  # 旋转量(度)
    speed: float = 50.0  # mm/s
    confidence: float = 0.0


@dataclass
class ManipulationState:
    """操作状态"""
    phase: str = "idle"  # approach/grasp/lift/move/place/release
    target_reached: bool = False
    object_detected: bool = False
    grasp_success: bool = False
    contact_force: float = 0.0
    current_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    error: str = ""


# ═══════════════════════════════════════════
# 1. 视觉伺服
# ═══════════════════════════════════════════

class VisualServo:
    """
    视觉伺服控制器
    基于特征点跟踪实现相机-目标对齐
    
    方法: Image-Based Visual Servoing (IBVS)
    """
    
    def __init__(self, camera_fx: float = 800.0, camera_fy: float = 800.0):
        self.fx = camera_fx
        self.fy = camera_fy
        self.detector = cv2.ORB_create(nfeatures=500)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        self.prev_kp = None
        self.prev_des = None
        self.prev_features = None
        self.lk_params = dict(winSize=(21, 21), maxLevel=3,
                              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01))
    
    def detect_target(self, image: np.ndarray, 
                      template: np.ndarray,
                      min_matches: int = 10) -> Optional[Dict]:
        """
        在图像中检测目标模板
        返回: {bbox, center, matches, homography}
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        gray_tpl = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if len(template.shape) == 3 else template
        
        kp, des = self.detector.detectAndCompute(gray, None)
        kp_tpl, des_tpl = self.detector.detectAndCompute(gray_tpl, None)
        
        if des is None or des_tpl is None or len(des) < min_matches:
            return None
        
        matches = self.matcher.knnMatch(des, des_tpl, k=2)
        good = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good.append(m)
        
        if len(good) < min_matches:
            return None
        
        src = np.float32([kp[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst = np.float32([kp_tpl[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        
        H, mask = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
        inliers = int(mask.sum()) if mask is not None else len(good)
        
        if H is None:
            return None
        
        h, w = gray_tpl.shape
        corners = np.float32([[0,0],[w,0],[w,h],[0,h]]).reshape(-1,1,2)
        warped = cv2.perspectiveTransform(corners, H)
        
        x_coords = warped[:, 0, 0]
        y_coords = warped[:, 0, 1]
        bbox = (int(x_coords.min()), int(y_coords.min()), 
                int(x_coords.max() - x_coords.min()), int(y_coords.max() - y_coords.min()))
        center = (int((x_coords.min() + x_coords.max()) / 2), 
                  int((y_coords.min() + y_coords.max()) / 2))
        
        # 存储当前帧特征用于跟踪
        self.prev_kp = kp
        self.prev_des = des
        self.prev_features = [kp[m.queryIdx].pt for m in good]
        
        return {"bbox": bbox, "center": center, "matches": len(good), 
                "inliers": inliers, "homography": H}
    
    def compute_servo_command(self, current: Dict, 
                               target_center: Tuple[int, int] = None,
                               target_size: Tuple[int, int] = None,
                               gain: float = 0.5) -> ServoCommand:
        """
        计算伺服命令 (移动相机使目标到达期望位置/尺寸)
        
        current: detect_target的返回值
        target_center: 期望目标在图像中的中心位置 (默认=图像中心)
        target_size: 期望目标的尺寸 (默认=当前尺寸, 不调深度)
        """
        if current is None:
            return ServoCommand(0, 0, 0, 0, 0, 0, confidence=0.0)
        
        cx, cy = current["center"]
        bbox = current["bbox"]
        
        if target_center is None:
            # 默认目标: 图像中心
            h, w = 640, 480  # 假设
            target_center = (w // 2, h // 2)
        
        # 像素误差 → mm移动 (使用焦距近似)
        err_x = target_center[0] - cx
        err_y = target_center[1] - cy
        
        dx = err_x * gain  # 简化: 1px ≈ gain mm
        dy = err_y * gain
        
        # 深度调整(基于目标尺寸变化)
        dz = 0.0
        if target_size is not None:
            curr_w, curr_h = bbox[2], bbox[3]
            if curr_w > 0:
                scale = target_size[0] / curr_w
                dz = (scale - 1.0) * 100 * gain  # 近似
        
        # 旋转(基于homography中的旋转分量)
        dyaw = 0.0
        if current.get("homography") is not None:
            H = current["homography"]
            angle = math.atan2(H[1, 0], H[0, 0]) * 180 / math.pi
            dyaw = -angle * gain
        
        confidence = current.get("inliers", 0) / max(current.get("matches", 1), 1)
        
        return ServoCommand(
            dx=dx, dy=dy, dz=dz,
            droll=0, dpitch=0, dyaw=dyaw,
            confidence=confidence
        )
    
    def track_features(self, image: np.ndarray) -> Optional[List[Tuple[float, float]]]:
        """光流跟踪 (LK跟踪器)"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        
        if self.prev_kp is None or self.prev_features is None:
            return None
        
        prev_pts = np.float32(self.prev_features).reshape(-1, 1, 2)
        next_pts, status, _ = cv2.calcOpticalFlowPyrLK(
            self._prev_gray, gray, prev_pts, None, **self.lk_params)
        
        self._prev_gray = gray.copy()
        
        if next_pts is None:
            return None
        
        tracked = [tuple(pt) for pt, st in zip(next_pts, status) if st == 1]
        return tracked if tracked else None
    
    def reset(self):
        """重置跟踪状态"""
        self.prev_kp = None
        self.prev_des = None
        self.prev_features = None


# ═══════════════════════════════════════════
# 2. 抓取规划
# ═══════════════════════════════════════════

class GraspPlanner:
    """
    抓取点规划
    基于几何分析确定最优抓取策略
    """
    
    def __init__(self):
        self.min_grasp_width = 20  # mm
        self.max_grasp_width = 150  # mm
    
    def plan(self, image: np.ndarray,
             bbox: Tuple[int, int, int, int],
             depth_map: Optional[np.ndarray] = None,
             object_mask: Optional[np.ndarray] = None) -> List[GraspPoint]:
        """
        规划抓取点
        bbox: 物体边界框 (x, y, w, h)
        返回: 抓取点列表(按质量排序)
        """
        x, y, w, h = bbox
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        grasps = []
        
        # === 方法1: 几何中心抓取 ===
        cx, cy = x + w // 2, y + h // 2
        
        # 估计抓取宽度(物体最窄可抓取维度)
        if object_mask is not None:
            # 在中心行/列找mask宽度
            row_mask = object_mask[cy, x:x+w]
            col_mask = object_mask[y:y+h, cx]
            h_width = np.sum(row_mask > 0)
            v_width = np.sum(col_mask > 0)
            grasp_w = min(h_width, v_width)
        else:
            grasp_w = min(w, h)
        
        quality = self._evaluate_grasp(gray, cx, cy, object_mask)
        
        if self.min_grasp_width <= grasp_w <= self.max_grasp_width:
            grasps.append(GraspPoint(
                x=cx, y=cy, approach_angle=0.0,
                width=float(grasp_w), quality=quality, method="top"
            ))
        
        # === 方法2: 边缘抓取(侧面) ===
        edge = cv2.Canny(gray, 50, 150)
        
        # 在物体边缘找直线段(抓取候选)
        roi_edge = edge[y:y+h, x:x+w]
        lines = cv2.HoughLinesP(roi_edge, 1, np.pi/180, 30, 
                                minLineLength=max(20, min(w,h)//4), 
                                maxLineGap=10)
        
        if lines is not None:
            for line in lines[:10]:
                lx1, ly1, lx2, ly2 = line[0]
                length = math.sqrt((lx2-lx1)**2 + (ly2-ly1)**2)
                angle = math.atan2(ly2-ly1, lx2-lx1) * 180 / math.pi
                
                # 只考虑近似水平的抓取线(±30°)
                if abs(angle % 180) > 30:
                    continue
                
                mid_x = int((lx1 + lx2) / 2) + x
                mid_y = int((ly1 + ly2) / 2) + y
                
                q = self._evaluate_grasp(gray, mid_x, mid_y, object_mask)
                approach = (angle + 90) % 360 - 180  # 垂直于边缘
                
                grasps.append(GraspPoint(
                    x=mid_x, y=mid_y,
                    approach_angle=approach,
                    width=float(length),
                    quality=q * 0.8,  # 边缘抓取质量略低
                    method="side"
                ))
        
        # === 方法3: 深度梯度抓取 ===
        if depth_map is not None and object_mask is not None:
            depth_grasps = self._plan_from_depth(gray, depth_map, object_mask, bbox)
            grasps.extend(depth_grasps)
        
        # 按质量排序
        grasps.sort(key=lambda g: -g.quality)
        return grasps[:5]  # 返回TOP5
    
    def _evaluate_grasp(self, gray: np.ndarray, x: int, y: int,
                        mask: Optional[np.ndarray] = None) -> float:
        """评估抓取点质量(0-1)"""
        h, w = gray.shape
        r = 20  # 评估半径
        
        x1, x2 = max(0, x-r), min(w, x+r)
        y1, y2 = max(0, y-r), min(h, y+r)
        
        if x2 <= x1 or y2 <= y1:
            return 0.0
        
        roi = gray[y1:y2, x1:x2]
        
        # 1. 边缘密度 (抓取点应靠近物体边缘而非中心空白)
        edge = cv2.Canny(roi, 50, 150)
        edge_density = np.sum(edge > 0) / edge.size
        
        # 2. 纹理均匀性 (均匀区域更易抓取)
        texture_var = np.std(roi) / 255.0
        
        # 3. 如果有mask, 检查抓取点是否在物体上
        mask_score = 0.5
        if mask is not None:
            mask_roi = mask[y1:y2, x1:x2]
            mask_ratio = np.sum(mask_roi > 0) / mask_roi.size
            # 最佳: 70-100% 在物体上
            mask_score = 1.0 - abs(mask_ratio - 0.85) * 2
        
        quality = (edge_density * 0.3 + (1 - texture_var) * 0.3 + mask_score * 0.4)
        return max(0.0, min(1.0, quality))
    
    def _plan_from_depth(self, gray: np.ndarray, depth: np.ndarray,
                         mask: np.ndarray, 
                         bbox: Tuple[int, int, int, int]) -> List[GraspPoint]:
        """基于深度梯度的抓取规划"""
        x, y, w, h = bbox
        grasps = []
        
        roi_depth = depth[y:y+h, x:x+w].copy()
        roi_mask = mask[y:y+h, x:x+w]
        
        # 只考虑物体区域
        roi_depth[roi_mask == 0] = 0
        
        # Sobel深度梯度 (高度变化=物体边缘=好的抓取点)
        gy = cv2.Sobel(roi_depth, cv2.CV_64F, 0, 1, ksize=5)
        
        # 找深度梯度最大的位置(物体前边缘)
        max_grad_rows = np.argmax(np.abs(gy), axis=1)
        
        for row_idx in range(0, len(max_grad_rows), max(1, len(max_grad_rows)//5)):
            col = max_grad_rows[row_idx]
            if roi_mask[row_idx, col] == 0:
                continue
            
            img_x = x + col
            img_y = y + row_idx
            
            q = self._evaluate_grasp(gray, img_x, img_y, mask)
            grasps.append(GraspPoint(
                x=img_x, y=img_y,
                approach_angle=0.0,
                width=float(min(w, 80)),
                quality=q * 0.7,
                method="depth_edge"
            ))
        
        return grasps
    
    def select_best_grasp(self, grasps: List[GraspPoint],
                           constraints: Dict = None) -> Optional[GraspPoint]:
        """
        选择最优抓取点
        constraints: {min_width, max_width, preferred_method}
        """
        if not grasps:
            return None
        
        if constraints is None:
            return grasps[0]
        
        min_w = constraints.get("min_width", self.min_grasp_width)
        max_w = constraints.get("max_width", self.max_grasp_width)
        preferred = constraints.get("preferred_method", None)
        
        filtered = [g for g in grasps if min_w <= g.width <= max_w]
        if preferred:
            pref = [g for g in filtered if g.method == preferred]
            if pref:
                return pref[0]
        
        return filtered[0] if filtered else grasps[0]


# ═══════════════════════════════════════════
# 3. 操作监控
# ═══════════════════════════════════════════

class ManipulationMonitor:
    """
    操作过程监控
    通过视觉反馈判断操作是否成功
    """
    
    def __init__(self):
        self.state = ManipulationState(phase="idle")
        self.prev_frame = None
        self.prev_objects = None
    
    def update(self, image: np.ndarray, 
               target_bbox: Tuple[int, int, int, int] = None,
               depth_map: np.ndarray = None) -> ManipulationState:
        """
        更新操作状态
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        h, w = gray.shape
        
        # === 检测运动 ===
        motion_score = 0.0
        if self.prev_frame is not None:
            diff = cv2.absdiff(gray, self.prev_frame)
            _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
            motion_score = np.sum(thresh > 0) / thresh.size
        
        self.prev_frame = gray.copy()
        
        # === 状态机 ===
        if self.state.phase == "idle":
            if target_bbox is not None:
                self.state.phase = "approach"
                self.state.object_detected = True
        
        elif self.state.phase == "approach":
            # 等待物体进入抓取区域
            if target_bbox:
                cx = target_bbox[0] + target_bbox[2] // 2
                cy = target_bbox[1] + target_bbox[3] // 2
                # 如果物体在图像中心区域
                if abs(cx - w/2) < w * 0.15 and abs(cy - h/2) < h * 0.15:
                    self.state.target_reached = True
                    self.state.phase = "grasp"
        
        elif self.state.phase == "grasp":
            # 检测是否抓取成功 (运动停止=可能已抓住)
            if motion_score < 0.01:
                self.state.grasp_success = True
                self.state.phase = "lift"
            elif motion_score > 0.1:
                # 大幅运动=可能失败
                self.state.error = "excessive_motion_during_grasp"
        
        elif self.state.phase == "lift":
            # 检测物体是否被抬起 (物体消失或深度变化)
            if motion_score < 0.005:
                self.state.phase = "move"
            elif motion_score > 0.15:
                self.state.error = "object_dropped"
                self.state.phase = "idle"
        
        elif self.state.phase == "move":
            if motion_score < 0.005:
                self.state.phase = "place"
        
        elif self.state.phase == "place":
            if motion_score > 0.1:
                # 物体被释放
                self.state.phase = "release"
        
        elif self.state.phase == "release":
            if motion_score < 0.005:
                self.state.phase = "idle"
        
        self.state.contact_force = motion_score * 100  # 近似
        return self.state
    
    def detect_picking_failure(self, before: np.ndarray, 
                                after: np.ndarray,
                                object_bbox: Tuple[int, int, int, int]) -> bool:
        """
        比较抓取前后的图像, 判断抓取是否成功
        成功: 物体从原位置消失
        失败: 物体仍在原位置
        """
        gray_b = cv2.cvtColor(before, cv2.COLOR_BGR2GRAY) if len(before.shape) == 3 else before
        gray_a = cv2.cvtColor(after, cv2.COLOR_BGR2GRAY) if len(after.shape) == 3 else after
        
        x, y, w, h = object_bbox
        roi_before = gray_b[y:y+h, x:x+w]
        roi_after = gray_a[y:y+h, x:x+w]
        
        # 计算ROI区域的变化
        diff = cv2.absdiff(roi_before, roi_after)
        change_ratio = np.sum(diff > 30) / diff.size
        
        # 大幅变化=物体被移走=成功
        return change_ratio > 0.3


# ═══════════════════════════════════════════
# 4. 运动轨迹规划
# ═══════════════════════════════════════════

class TrajectoryPlanner:
    """
    基于视觉约束的轨迹规划
    """
    
    @staticmethod
    def plan_pick_and_place(start_3d: Tuple[float, float, float],
                            end_3d: Tuple[float, float, float],
                            approach_height: float = 100.0,
                            n_points: int = 20) -> List[Tuple[float, float, float]]:
        """
        规划 pick-and-place 轨迹
        返回: 路径点列表 [(x, y, z), ...]
        
        轨迹: start → above_start → start → above_start → 
               above_end → end → above_end
        """
        sx, sy, sz = start_3d
        ex, ey, ez = end_3d
        
        # 关键点
        above_start = (sx, sy, sz + approach_height)
        above_end = (ex, ey, ez + approach_height)
        
        # 各段路径
        def lerp(p1, p2, n):
            return [tuple(p1[j] + (p2[j]-p1[j]) * i/n for j in range(3)) for i in range(n+1)]
        
        trajectory = []
        trajectory.extend(lerp(start_3d, above_start, n_points//4))      # 抬起
        trajectory.extend(lerp(above_start, above_end, n_points//2))      # 移动
        trajectory.extend(lerp(above_end, end_3d, n_points//4))          # 下降
        
        return trajectory
    
    @staticmethod
    def check_collision(trajectory: List[Tuple[float, float, float]],
                        obstacles: List[Tuple[float, float, float, float, float, float]],
                        margin: float = 20.0) -> List[int]:
        """
        碰撞检测
        obstacles: [(x_min, y_min, z_min, x_max, y_max, z_max), ...]
        返回: 碰撞点索引列表
        """
        collisions = []
        for i, (px, py, pz) in enumerate(trajectory):
            for obs in obstacles:
                ox1, oy1, oz1, ox2, oy2, oz2 = obs
                if (ox1 - margin <= px <= ox2 + margin and
                    oy1 - margin <= py <= oy2 + margin and
                    oz1 - margin <= pz <= oz2 + margin):
                    collisions.append(i)
                    break
        return collisions
    
    @staticmethod
    def avoid_collision(trajectory: List[Tuple[float, float, float]],
                        collision_indices: List[int],
                        obstacles: List[Tuple[float, float, float, float, float, float]],
                        clearance: float = 50.0) -> List[Tuple[float, float, float]]:
        """
        简单碰撞规避: 在碰撞点上方添加绕行点
        """
        if not collision_indices:
            return trajectory
        
        modified = list(trajectory)
        safe_z = max(p[2] for p in trajectory) + clearance
        
        for idx in sorted(set(collision_indices)):
            px, py, pz = modified[idx]
            modified[idx] = (px, py, safe_z)
        
        # 平滑绕行(在碰撞点前后添加过渡点)
        if collision_indices:
            ci = collision_indices[0]
            if ci > 0:
                prev = modified[ci - 1]
                curr = modified[ci]
                modified.insert(ci, (curr[0], curr[1], (prev[2] + curr[2]) / 2))
        
        return modified


# ═══════════════════════════════════════════
# 统一动作视觉接口
# ═══════════════════════════════════════════

class ActionVision:
    """统一动作视觉接口"""
    
    def __init__(self):
        self.servo = VisualServo()
        self.grasp = GraspPlanner()
        self.monitor = ManipulationMonitor()
        self.trajectory = TrajectoryPlanner()
    
    def plan_grasp(self, image: np.ndarray, bbox: Tuple[int, int, int, int],
                   depth_map: np.ndarray = None) -> List[GraspPoint]:
        """规划抓取"""
        return self.grasp.plan(image, bbox, depth_map)
    
    def plan_pick_place(self, start: Tuple, end: Tuple) -> List[Tuple]:
        """规划取放轨迹"""
        return self.trajectory.plan_pick_and_place(start, end)


if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "/Users/administruter/Desktop/803fab503407aa9fd58885c30ec832ff.jpg"
    img = cv2.imread(path)
    if img is None:
        print(f"无法读取: {path}"); sys.exit(1)
    
    print(f"动作视觉测试: {path}")
    
    av = ActionVision()
    
    # 抓取规划
    grasps = av.plan_grasp(img, (100, 200, 800, 600))
    print(f"\n抓取点 ({len(grasps)}个):")
    for g in grasps:
        print(f"  ({g.x}, {g.y}) angle={g.approach_angle:.0f}° "
              f"width={g.width:.0f}px quality={g.quality:.2f} method={g.method}")
    
    # 轨迹规划
    traj = av.plan_pick_place((0, 0, 0), (300, 200, 0))
    print(f"\n取放轨迹: {len(traj)} 点")
    print(f"  起点: {traj[0]}")
    print(f"  终点: {traj[-1]}")
    print(f"  最高点: {max(traj, key=lambda p: p[2])}")
    
    # 碰撞检测
    obs = [(100, 100, 100, 200, 200, 150)]
    collisions = av.trajectory.check_collision(traj, obs)
    print(f"  碰撞点: {collisions}")
    
    if collisions:
        safe_traj = av.trajectory.avoid_collision(traj, collisions, obs)
        safe_collisions = av.trajectory.check_collision(safe_traj, obs)
        print(f"  规避后碰撞: {safe_collisions}")
    
    print(f"\n✅ 动作视觉测试完成")
