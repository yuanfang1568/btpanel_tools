#!/usr/bin/env python3
"""
宝塔面板工具性能测试脚本
用于测试优化前后的性能差异
"""

import time
import subprocess
import statistics
import json
import os
import sys
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TestResult:
    """测试结果数据类"""
    test_name: str
    original_time: float
    optimized_time: float
    improvement_percent: float
    success: bool
    error_message: str = ""

class PerformanceTester:
    """性能测试器"""
    
    def __init__(self):
        self.results: List[TestResult] = []
        self.test_count = 0
        
    def run_test(self, test_name: str, original_func, optimized_func, *args, **kwargs) -> TestResult:
        """运行单个测试"""
        self.test_count += 1
        print(f"运行测试 {self.test_count}: {test_name}")
        
        # 测试原始版本
        original_time = 0
        original_success = False
        try:
            start_time = time.time()
            original_result = original_func(*args, **kwargs)
            original_time = time.time() - start_time
            original_success = True
        except Exception as e:
            original_error = str(e)
            print(f"  原始版本失败: {original_error}")
        
        # 测试优化版本
        optimized_time = 0
        optimized_success = False
        try:
            start_time = time.time()
            optimized_result = optimized_func(*args, **kwargs)
            optimized_time = time.time() - start_time
            optimized_success = True
        except Exception as e:
            optimized_error = str(e)
            print(f"  优化版本失败: {optimized_error}")
        
        # 计算改进百分比
        if original_time > 0 and optimized_time > 0:
            improvement = ((original_time - optimized_time) / original_time) * 100
        else:
            improvement = 0
        
        # 创建测试结果
        result = TestResult(
            test_name=test_name,
            original_time=original_time,
            optimized_time=optimized_time,
            improvement_percent=improvement,
            success=original_success and optimized_success,
            error_message=f"Original: {original_error if not original_success else 'OK'}, "
                         f"Optimized: {optimized_error if not optimized_success else 'OK'}"
        )
        
        self.results.append(result)
        
        # 打印结果
        if result.success:
            print(f"  原始版本: {original_time:.4f}s")
            print(f"  优化版本: {optimized_time:.4f}s")
            print(f"  改进: {improvement:.2f}%")
        else:
            print(f"  测试失败: {result.error_message}")
        
        print()
        return result
    
    def test_shell_script_performance(self):
        """测试Shell脚本性能"""
        print("=== Shell脚本性能测试 ===")
        
        # 测试脚本启动时间
        def test_script_startup(script_path):
            try:
                start_time = time.time()
                result = subprocess.run(['bash', script_path, '--help'], 
                                      capture_output=True, timeout=30)
                return time.time() - start_time
            except subprocess.TimeoutExpired:
                return 30.0
            except Exception:
                return 0.0
        
        # 测试网络连接
        def test_network_connection():
            try:
                start_time = time.time()
                result = subprocess.run(['curl', '-s', '--connect-timeout', '10', 
                                       'https://api.bt.cn'], 
                                      capture_output=True, timeout=15)
                return time.time() - start_time
            except subprocess.TimeoutExpired:
                return 15.0
            except Exception:
                return 0.0
        
        # 测试文件操作
        def test_file_operations():
            test_file = "/tmp/performance_test.txt"
            try:
                start_time = time.time()
                # 创建文件
                with open(test_file, 'w') as f:
                    f.write("test" * 1000)
                # 读取文件
                with open(test_file, 'r') as f:
                    content = f.read()
                # 删除文件
                os.remove(test_file)
                return time.time() - start_time
            except Exception:
                return 0.0
        
        # 运行测试
        if os.path.exists("btpanel_tools.sh"):
            self.run_test("脚本启动时间", 
                         lambda: test_script_startup("btpanel_tools.sh"),
                         lambda: test_script_startup("btpanel_tools_optimized.sh"))
        
        self.run_test("网络连接测试", 
                     lambda: test_network_connection(),
                     lambda: test_network_connection())
        
        self.run_test("文件操作测试", 
                     lambda: test_file_operations(),
                     lambda: test_file_operations())
    
    def test_python_library_performance(self):
        """测试Python库性能"""
        print("=== Python库性能测试 ===")
        
        try:
            # 导入原始库
            sys.path.insert(0, '.')
            import request as original_request
            
            # 导入优化库
            import request_optimized as optimized_request
            
            # 测试HTTP请求
            def test_http_request(lib):
                try:
                    start_time = time.time()
                    response = lib.urlopen('https://httpbin.org/get', timeout=10)
                    response.read()
                    return time.time() - start_time
                except Exception:
                    return 0.0
            
            # 测试连接池
            def test_connection_pool(lib):
                try:
                    start_time = time.time()
                    for i in range(5):
                        response = lib.urlopen('https://httpbin.org/get', timeout=5)
                        response.read()
                    return time.time() - start_time
                except Exception:
                    return 0.0
            
            # 测试错误处理
            def test_error_handling(lib):
                try:
                    start_time = time.time()
                    try:
                        lib.urlopen('https://invalid-domain-12345.com', timeout=5)
                    except:
                        pass
                    return time.time() - start_time
                except Exception:
                    return 0.0
            
            # 运行测试
            self.run_test("HTTP请求测试", 
                         lambda: test_http_request(original_request),
                         lambda: test_http_request(optimized_request))
            
            self.run_test("连接池测试", 
                         lambda: test_connection_pool(original_request),
                         lambda: test_connection_pool(optimized_request))
            
            self.run_test("错误处理测试", 
                         lambda: test_error_handling(original_request),
                         lambda: test_error_handling(optimized_request))
            
        except ImportError as e:
            print(f"无法导入测试库: {e}")
    
    def test_javascript_performance(self):
        """测试JavaScript性能"""
        print("=== JavaScript性能测试 ===")
        
        # 这里可以添加JavaScript性能测试
        # 由于需要在浏览器环境中运行，这里只是示例
        print("JavaScript性能测试需要在浏览器环境中进行")
        print("可以使用以下工具进行测试:")
        print("- Chrome DevTools Performance面板")
        print("- Lighthouse")
        print("- WebPageTest")
    
    def generate_report(self) -> Dict:
        """生成测试报告"""
        successful_tests = [r for r in self.results if r.success]
        
        if not successful_tests:
            return {"error": "没有成功的测试"}
        
        # 计算统计信息
        improvements = [r.improvement_percent for r in successful_tests]
        avg_improvement = statistics.mean(improvements)
        max_improvement = max(improvements)
        min_improvement = min(improvements)
        
        # 按测试类型分组
        test_categories = {}
        for result in successful_tests:
            category = result.test_name.split()[0]
            if category not in test_categories:
                test_categories[category] = []
            test_categories[category].append(result.improvement_percent)
        
        # 计算每个类别的平均改进
        category_improvements = {}
        for category, improvements in test_categories.items():
            category_improvements[category] = statistics.mean(improvements)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(self.results),
            "successful_tests": len(successful_tests),
            "success_rate": len(successful_tests) / len(self.results) * 100,
            "average_improvement": avg_improvement,
            "max_improvement": max_improvement,
            "min_improvement": min_improvement,
            "category_improvements": category_improvements,
            "detailed_results": [
                {
                    "test_name": r.test_name,
                    "original_time": r.original_time,
                    "optimized_time": r.optimized_time,
                    "improvement_percent": r.improvement_percent
                }
                for r in successful_tests
            ]
        }
        
        return report
    
    def print_summary(self):
        """打印测试总结"""
        print("\n" + "="*50)
        print("性能测试总结")
        print("="*50)
        
        successful_tests = [r for r in self.results if r.success]
        
        if not successful_tests:
            print("没有成功的测试")
            return
        
        improvements = [r.improvement_percent for r in successful_tests]
        avg_improvement = statistics.mean(improvements)
        
        print(f"总测试数: {len(self.results)}")
        print(f"成功测试数: {len(successful_tests)}")
        print(f"成功率: {len(successful_tests)/len(self.results)*100:.1f}%")
        print(f"平均性能改进: {avg_improvement:.2f}%")
        print(f"最大改进: {max(improvements):.2f}%")
        print(f"最小改进: {min(improvements):.2f}%")
        
        print("\n详细结果:")
        for result in successful_tests:
            print(f"  {result.test_name}: {result.improvement_percent:.2f}%")
    
    def save_report(self, filename: str = "performance_report.json"):
        """保存测试报告到文件"""
        report = self.generate_report()
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"\n测试报告已保存到: {filename}")

def main():
    """主函数"""
    print("宝塔面板工具性能测试")
    print("="*50)
    
    tester = PerformanceTester()
    
    # 运行各种测试
    tester.test_shell_script_performance()
    tester.test_python_library_performance()
    tester.test_javascript_performance()
    
    # 生成报告
    tester.print_summary()
    tester.save_report()
    
    print("\n测试完成!")

if __name__ == "__main__":
    main()