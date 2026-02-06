import nbtlib
from pathlib import Path
from collections import Counter, defaultdict
import sys


def analyze_block_usage(input_file):
    """
    分析.schem文件中非空气方块的使用数量

    参数:
        input_file: 输入的.schem文件路径
    """
    try:
        print(f"正在分析文件: {input_file}")

        # 使用nbtlib加载文件
        nbt_file = nbtlib.load(input_file)

        # 获取结构尺寸
        width = nbt_file['Width']
        length = nbt_file['Length']
        height = nbt_file['Height']
        total_blocks = width * length * height

        print(f"结构尺寸: {width}x{length}x{height}")
        print(f"总方块数: {total_blocks}")

        # 获取调色板和方块数据
        palette = nbt_file['Palette']
        block_data = nbt_file['BlockData']

        # 统计方块使用情况
        block_counter = Counter()
        index_to_block = {}

        # 构建索引到方块名称的映射
        for block_name, index in palette.items():
            index_to_block[index] = block_name
            # 初始化计数器
            block_counter[block_name] = 0

        # 统计每个方块的使用次数
        for block_index in block_data:
            block_name = index_to_block.get(block_index)
            if block_name:
                block_counter[block_name] += 1

        # 过滤掉空气方块并排序
        non_air_blocks = {}
        total_non_air = 0

        for block_name, count in block_counter.items():
            if not is_air_block(block_name):
                non_air_blocks[block_name] = count
                total_non_air += count

        # 按使用数量降序排序
        sorted_blocks = sorted(non_air_blocks.items(), key=lambda x: x[1], reverse=True)

        # 按命名空间分组统计
        namespace_stats = defaultdict(int)
        for block_name, count in sorted_blocks:
            namespace = extract_namespace(block_name)
            namespace_stats[namespace] += count

        # 输出统计结果
        print("\n" + "=" * 60)
        print("非空气方块使用统计")
        print("=" * 60)
        print(f"总非空气方块数: {total_non_air}")
        print(f"空气方块数: {total_blocks - total_non_air}")
        print(f"非空气方块占比: {total_non_air / total_blocks * 100:.2f}%")

        print("\n按命名空间统计:")
        print("-" * 40)
        for namespace, count in sorted(namespace_stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  {namespace}: {count} 个方块 ({count / total_non_air * 100:.1f}%)")

        print("\n详细方块使用统计 (按数量降序):")
        print("-" * 60)
        for i, (block_name, count) in enumerate(sorted_blocks, 1):
            percentage = count / total_non_air * 100
            print(f"{i:2d}. {block_name:<50} : {count:>4} 个 ({percentage:5.1f}%)")

        # 生成统计报告文件
        generate_statistics_report(input_file, width, length, height, total_blocks,
                                   total_non_air, sorted_blocks, namespace_stats)

        return True

    except Exception as e:
        print(f"分析文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def is_air_block(block_name):
    """判断是否为空气方块"""
    air_identifiers = ['air', 'minecraft:air', 'void_air', 'minecraft:void_air',
                       'cave_air', 'minecraft:cave_air']
    return block_name in air_identifiers or 'air' in block_name.lower()


def extract_namespace(block_name):
    """从方块ID中提取命名空间"""
    if ':' in block_name:
        return block_name.split(':')[0]
    else:
        return 'minecraft'  # 默认命名空间


def generate_statistics_report(input_file, width, length, height, total_blocks,
                               total_non_air, sorted_blocks, namespace_stats):
    """生成详细的统计报告文件"""
    input_path = Path(input_file)
    report_file = input_path.parent / f"{input_path.stem}_block_statistics.txt"

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write("方块使用统计报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"文件: {input_path.name}\n")
        f.write(f"结构尺寸: {width}x{length}x{height}\n")
        f.write(f"总方块数: {total_blocks}\n")
        f.write(f"非空气方块数: {total_non_air}\n")
        f.write(f"空气方块数: {total_blocks - total_non_air}\n")
        f.write(f"非空气方块占比: {total_non_air / total_blocks * 100:.2f}%\n\n")

        f.write("按命名空间统计:\n")
        f.write("-" * 40 + "\n")
        for namespace, count in sorted(namespace_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = count / total_non_air * 100
            f.write(f"{namespace:<20} : {count:>4} 个 ({percentage:5.1f}%)\n")

        f.write("\n详细方块使用统计 (按数量降序):\n")
        f.write("-" * 80 + "\n")
        for i, (block_name, count) in enumerate(sorted_blocks, 1):
            percentage_total = count / total_blocks * 100
            percentage_non_air = count / total_non_air * 100
            f.write(
                f"{i:3d}. {block_name:<60} : {count:>5} 个 (总计{percentage_total:5.1f}%, 非空气{percentage_non_air:5.1f}%)\n")

    print(f"\n统计报告已保存至: {report_file}")


def main():
    """
    主函数，处理命令行参数或交互式输入
    """
    if len(sys.argv) > 1:
        # 使用命令行参数
        input_file = sys.argv[1]
    else:
        # 交互式输入
        input_file = input("请输入.schem文件路径: ").strip()

    # 检查文件是否存在
    if not Path(input_file).exists():
        print(f"错误: 文件 {input_file} 不存在")
        return

    # 检查文件扩展名
    if not input_file.lower().endswith(('.schem', '.schematic')):
        print("警告: 文件扩展名不是.schem或.schematic，可能不是有效的结构文件")
        proceed = input("是否继续? (y/n): ").strip().lower()
        if proceed != 'y':
            return

    # 分析方块使用情况
    success = analyze_block_usage(input_file)

    if success:
        print("\n方块统计完成！")
    else:
        print("\n方块统计失败！")


if __name__ == "__main__":
    main()