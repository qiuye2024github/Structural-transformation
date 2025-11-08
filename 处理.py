import nbtlib
from nbtlib import Compound
import sys
from pathlib import Path


def remove_block_states_from_schem(input_file, output_file=None):
    """
    从.schem文件中删除Palette中每个方块ID后面的方括号及其内容（方块状态数据）
    如果出现重复的基本方块ID，只保留第一次出现的数字索引，并将后续重复的方块ID对应的数字索引替换为第一次出现的数字索引

    参数:
        input_file: 输入的.schem文件路径
        output_file: 输出的.schem文件路径，如果为None则覆盖原文件
    """
    try:
        # 确定输出文件路径
        if output_file is None:
            output_path = input_file
        else:
            output_path = output_file

        print(f"正在处理文件: {input_file}")

        # 使用nbtlib.load加载文件
        nbt_file = nbtlib.load(input_file)

        # 获取Palette
        palette = nbt_file['Palette']

        # 获取BlockData
        block_data = nbt_file['BlockData']

        # 创建一个新的Palette，移除方块状态数据
        new_palette = Compound()
        # 用于记录基本方块ID和对应的第一次出现的数字索引
        base_id_to_index = {}
        # 用于记录需要替换的索引映射关系
        index_mapping = {}
        removed_count = 0
        duplicate_count = 0

        # 第一次遍历：处理Palette，构建新Palette和索引映射
        for block_id_with_states, index in palette.items():
            # 提取基本方块ID（移除方括号及其内容）
            if '[' in block_id_with_states:
                base_block_id = block_id_with_states.split('[')[0]
                removed_count += 1
            else:
                base_block_id = block_id_with_states

            # 检查基本方块ID是否已经存在
            if base_block_id in base_id_to_index:
                # 记录索引映射关系：将当前索引映射到第一次出现的索引
                first_index = base_id_to_index[base_block_id]
                index_mapping[index] = first_index
                print(f"发现重复方块ID: {base_block_id}, 将索引 {index} 映射到 {first_index}")
                duplicate_count += 1
            else:
                # 第一次出现这个基本方块ID，记录它
                base_id_to_index[base_block_id] = index
                new_palette[base_block_id] = index
                print(f"添加方块ID: {base_block_id} -> {index}")

        # 第二次遍历：更新BlockData中的索引
        if index_mapping:
            print(f"开始更新BlockData中的索引映射...")
            # 将BlockData转换为列表以便修改
            block_data_list = list(block_data)

            for i in range(len(block_data_list)):
                current_index = block_data_list[i]
                if current_index in index_mapping:
                    block_data_list[i] = index_mapping[current_index]

            # 将修改后的列表转换回nbtlib的IntArray
            nbt_file['BlockData'] = nbtlib.IntArray(block_data_list)
            print(f"更新了BlockData中的 {len([x for x in block_data_list if x in index_mapping])} 个索引")

        # 更新Palette
        nbt_file['Palette'] = new_palette

        # 使用上下文管理器自动保存
        with nbt_file as file_obj:
            # 在上下文管理器中使用文件对象
            pass

        print(f"处理完成！移除了 {removed_count} 个方块的状态数据")
        print(f"处理了 {duplicate_count} 个重复的方块ID")
        print(f"输出文件: {output_path}")

    except Exception as e:
        print(f"处理文件时出错: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

    return True


def main():
    """
    主函数，处理命令行参数或交互式输入
    """
    if len(sys.argv) > 1:
        # 使用命令行参数
        input_file = sys.argv[1]

        if len(sys.argv) > 2:
            output_file = sys.argv[2]
        else:
            # 如果没有指定输出文件，在原文件名后添加 "_clean"
            input_path = Path(input_file)
            output_file = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
    else:
        # 交互式输入
        input_file = input("请输入.schem文件路径: ").strip()

        overwrite = input("是否覆盖原文件? (y/n, 默认n): ").strip().lower()
        if overwrite == 'y':
            output_file = None
        else:
            input_path = Path(input_file)
            output_file = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
            print(f"将保存为: {output_file}")

    # 处理文件
    if not Path(input_file).exists():
        print(f"错误: 文件 {input_file} 不存在")
        return

    success = remove_block_states_from_schem(input_file, output_file)

    if success:
        print("方块状态移除成功！")
    else:
        print("方块状态移除失败！")


if __name__ == "__main__":
    main()