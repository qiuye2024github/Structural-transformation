import string
from pathlib import Path
import nbtlib

# ----------------------
# 配置区
# ----------------------
INPUT_FILE = "通能炉.schem"  # 改为.schem文件
OUTPUT_ROOT = "multiblock"  # 固定第一层目录
PACKAGE_NAME = "cn.qiuye.gtl_extend.common.data.machines.MultiBlock"
LAYERS_PER_FILE = 100
CLASS_PREFIX = "SuperfluidGeneralEnergyFurnace"
BASE_STRUCTURE = "FactoryBlockPattern.start()"

# 从输入文件名获取结构名称
STRUCTURE_DIR = Path(INPUT_FILE).stem

# 定义可用单符号（移除了指定的特殊字符）
CHAR_CATEGORIES = [
    list(string.ascii_uppercase),  # 第一优先级：大写字母
    list(string.ascii_lowercase),  # 第二优先级：小写字母
    list(string.digits),  # 第三优先级：数字
    ['!', '@', '#', '$', '%', '^', '&', '*', '-', '+', '=']  # 最后：特殊符号
]

SPECIAL_CHARS = {
    '~': {
        'condition': "Predicates.controller(blocks(definition.getBlock()))",  # 修复：添加缺失的右括号
        'keywords': [  # 新增通用识别关键词
            'gtl_extend:superfluid_general_energy_furnace'
        ]
    }
}
COMPLEX_CONDITIONS = {
    "A": {
        "condition": "Predicates.blocks(GetRegistries.getBlock('{}'))",  # 修复：添加缺失的右括号
        "keywords": ["gtceu:high_temperature_smelting_casing"],
        "chain": [  # 移除.setMinGlobalLimited(10)
            {
                "or": [
                    "Predicates.abilities(PartAbility.EXPORT_ITEMS).setPreviewCount(1)",
                    "Predicates.abilities(PartAbility.IMPORT_ITEMS).setPreviewCount(1)",
                    "Predicates.abilities(PartAbility.EXPORT_FLUIDS).setPreviewCount(1)",
                    "Predicates.abilities(PartAbility.IMPORT_FLUIDS).setPreviewCount(1)",
                    "Predicates.abilities(PartAbility.INPUT_LASER).setMaxGlobalLimited(0)",
                    "Predicates.abilities(PartAbility.INPUT_ENERGY).setMaxGlobalLimited(0)"
                ]
            }
        ]
    }
}


# ----------------------
# 核心逻辑
# ----------------------
class SchematicConverter:
    def __init__(self):
        self.output_dir = Path(OUTPUT_ROOT) / STRUCTURE_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.palette = {}
        self.block_data = []
        self.width = 0
        self.length = 0
        self.height = 0
        self.auto_char_map = {}
        self.used_chars = set(SPECIAL_CHARS.keys()) | set(COMPLEX_CONDITIONS.keys())
        self.char_generator = self.create_char_generator()
        self.layers = []  # 显式初始化实例变量

    def create_char_generator(self):
        """字符生成序列：按类别优先级分配字符"""
        # 按优先级顺序遍历所有字符类别
        for category in CHAR_CATEGORIES:
            for symbol in category:
                if symbol not in self.used_chars:
                    yield symbol

        # 如果所有字符都不够用，抛出错误
        raise ValueError("字符资源耗尽，请减少唯一方块种类")

    def load_schematic(self, file_path):
        """加载并解析.schem文件"""
        try:
            # 使用nbtlib加载.schem文件
            nbt_data = nbtlib.load(file_path)

            # 获取结构尺寸
            self.width = nbt_data['Width']
            self.length = nbt_data['Length']
            self.height = nbt_data['Height']

            print(f"结构尺寸: {self.width}x{self.length}x{self.height}")

            # 解析调色板
            self.parse_nbt_palette(nbt_data['Palette'])

            # 解析方块数据
            self.decode_nbt_block_data(nbt_data['BlockData'])

        except Exception as err:
            raise ValueError(f"解析.schem文件失败: {str(err)}")

    def parse_nbt_palette(self, palette_tag):
        """解析NBT调色板数据"""
        # NBT调色板是字典，键是方块ID，值是调色板索引
        entries = []

        for block_name, palette_id in palette_tag.items():
            entries.append((block_name, palette_id))

        # 按调色板索引排序
        entries.sort(key=lambda x: x[1])

        # 处理特殊方块
        for block_name, palette_id in entries:
            # 空气方块处理
            if block_name == "minecraft:air" or block_name == "air":
                self._handle_air_block(palette_id)
                continue

            # 特殊字符匹配（基于配置的关键词）
            matched_special = False
            for char, config in SPECIAL_CHARS.items():
                keywords = config.get('keywords', [])
                for keyword in keywords:
                    if block_name.lower() == keyword.lower():
                        self.palette[palette_id] = char
                        self.auto_char_map[block_name] = char
                        print(f"识别到特殊条件方块 {block_name} -> {char}")
                        matched_special = True
                        break  # 匹配到一个关键词即退出循环
                if matched_special:
                    break  # 已匹配特殊字符，退出外层循环
            if matched_special:
                continue  # 继续处理下一个方块

            matched_complex = False
            for char, config in COMPLEX_CONDITIONS.items():
                keywords = config.get('keywords', [])
                for keyword in keywords:
                    if keyword.lower() in block_name.lower():
                        self.palette[palette_id] = char
                        self.auto_char_map[block_name] = char
                        self.used_chars.add(char)
                        print(f"识别到复杂条件方块 {block_name} -> {char} (关键词: {keyword})")
                        matched_complex = True
                        break
                if matched_complex:
                    break
            if matched_complex:
                continue

            # 自动分配字符（使用单符号）
            if block_name not in self.auto_char_map:
                try:
                    new_char = next(self.char_generator)
                    while new_char in self.used_chars:
                        new_char = next(self.char_generator)
                    self.auto_char_map[block_name] = new_char
                    self.used_chars.add(new_char)
                    print(f"自动分配 {block_name} -> {new_char}")
                except StopIteration as stop_exception:
                    raise ValueError("单符号资源耗尽，请减少唯一方块种类") from stop_exception

            # 更新palette映射
            assigned_char = self.auto_char_map[block_name]
            self.palette[palette_id] = assigned_char
            print(f"映射 {block_name} (ID:{palette_id}) -> {assigned_char}")

    def _handle_air_block(self, palette_id):
        """特殊处理空气方块"""
        # 修复：确保palette_id是整数，并正确处理所有类型的palette_id
        try:
            palette_id_int = int(palette_id)
        except (ValueError, TypeError):
            # 如果无法转换为整数，尝试其他方式处理
            palette_id_int = palette_id

        self.palette[palette_id_int] = ' '
        self.auto_char_map["minecraft:air"] = ' '
        self.auto_char_map["air"] = ' '
        self.used_chars.add(' ')

    def decode_nbt_block_data(self, block_data_tag):
        """解析NBT方块数据"""
        self.block_data = []

        # BlockData可能是字节数组或整数数组
        if hasattr(block_data_tag, '__iter__'):
            # 直接迭代数组
            for block_id in block_data_tag:
                # 确保block_id是palette字典中存在的键
                if block_id not in self.palette:
                    # 尝试转换为整数
                    try:
                        block_id_int = int(block_id)
                        if block_id_int in self.palette:
                            self.block_data.append(block_id_int)
                            continue
                    except (ValueError, TypeError):
                        pass
                    raise ValueError(f"发现未映射的方块ID: {block_id}")
                self.block_data.append(block_id)
        else:
            # 单个值的情况（理论上不应该出现）
            block_id = int(block_data_tag)
            if block_id not in self.palette:
                raise ValueError(f"发现未映射的方块ID: {block_id}")
            self.block_data.append(block_id)

        # 数据校验：width * length * height = 块数据总量
        expected_size = self.width * self.length * self.height
        if len(self.block_data) != expected_size:
            raise ValueError(f"数据长度不匹配！预期: {expected_size}, 实际: {len(self.block_data)}")

    def generate_layers(self):
        self.layers = []

        # Z轴从小到大遍历（每个Z对应一个LAYER）
        for z in range(self.length):
            layer_data = []  # 修复：避免与实例变量名冲突

            # Y轴从下到上（y=0为最下层）
            for y in range(self.height):
                row = []

                # X轴从左到右
                for x in range(self.width):
                    # 修正索引公式：y * (width * length) + z * width + x
                    index = y * (self.width * self.length) + z * self.width + x
                    if index < len(self.block_data):
                        block_id = self.block_data[index]
                        row.append(self.palette.get(block_id, '?'))
                    else:
                        row.append('?')  # 索引超出范围
                layer_data.append("".join(row))

            self.layers.append(layer_data)

        return self.layers  # 返回实例变量

    def generate_java_code(self, data):
        """生成Java结构类文件"""
        total_files = (len(data) + LAYERS_PER_FILE - 1) // LAYERS_PER_FILE
        for file_num in range(total_files):
            start = file_num * LAYERS_PER_FILE
            end = min((file_num + 1) * LAYERS_PER_FILE, len(data))
            file_layers = data[start:end]

            class_name = f"{CLASS_PREFIX}_Part{file_num + 1}"
            code = [
                f"package {PACKAGE_NAME}.{STRUCTURE_DIR};",
                "",
                f"public class {class_name} {{",
                ""
            ]

            # 修正：每个文件内的层号应该从1开始，而不是start+1
            for i, layer in enumerate(file_layers, 1):  # 改为从1开始
                code.append(f"    public static final String[] LAYER_{i:03} = {{")
                code.extend([f'        "{row}",' for row in layer])
                code.append("    };\n")

            code.append("}")
            output_file = self.output_dir / f"{class_name}.java"

            # 删除重复的写入操作，只写一次文件
            output_file.write_text("\n".join(code), encoding="utf-8")
            print(f"生成结构类文件: {output_file}")

    def generate_pattern_code_snippet(self):
        """生成主模式类文件（只包含aisle部分，返回Builder）"""
        main_class_name = CLASS_PREFIX

        code = [
            f"package {PACKAGE_NAME}.{STRUCTURE_DIR};",
            "",
            "import com.gregtechceu.gtceu.api.pattern.FactoryBlockPattern;",
            "",
            f"public class {main_class_name} {{",
            "",
            "    public static final FactoryBlockPattern.Builder PATTERN;",
            "",
            "    static {",
            f"        PATTERN = {BASE_STRUCTURE}"
        ]

        # 生成所有层的aisle调用
        total_layers = len(self.layers)
        for layer_idx in range(total_layers):
            part_num = (layer_idx // LAYERS_PER_FILE) + 1
            layer_in_part = (layer_idx % LAYERS_PER_FILE) + 1
            class_name = f"{CLASS_PREFIX}_Part{part_num}"
            layer_ref = f"{class_name}.LAYER_{layer_in_part:03}"
            code.append(f"                .aisle({layer_ref})")

        code.append("    }")
        code.append("}")

        output_file = self.output_dir / f"{main_class_name}.java"
        output_file.write_text("\n".join(code), encoding="utf-8")
        print(f"生成主模式类文件: {output_file}")

        # 单独生成.where()条件和.build()用于手动粘贴
        self.generate_conditions_for_manual_paste()

    def generate_conditions_for_manual_paste(self):
        """生成单独的.where()条件和.build()，用于手动粘贴到机器类"""
        conditions_code = []

        unique_chars = set()
        for layer in self.layers:
            for row in layer:
                unique_chars.update(row)

        processed_chars = set()

        for char in sorted(unique_chars, key=lambda x: (x not in SPECIAL_CHARS, x)):
            if char == ' ':  # 跳过空气方块
                conditions_code.append(f"                .where(' ', Predicates.any())")
                processed_chars.add(char)
                continue

            # 跳过已处理的字符
            if char in processed_chars:
                continue

            if char in SPECIAL_CHARS:
                # 处理特殊字符（如~）
                config = SPECIAL_CHARS[char]
                # 修复：特殊字符条件不需要格式化
                conditions_code.append(f"                .where('{char}', {config['condition']})")
                processed_chars.add(char)

            elif char in COMPLEX_CONDITIONS:
                # 处理复杂条件（如A）
                config = COMPLEX_CONDITIONS[char]
                matched_blocks = [k for k, v in self.auto_char_map.items() if v == char]
                if matched_blocks:
                    base_condition = config['condition'].format(matched_blocks[0])

                    # 构建复杂条件链
                    condition_lines = [base_condition]
                    for chain_item in config.get('chain', []):
                        if 'or' in chain_item:
                            for or_condition in chain_item['or']:
                                condition_lines.append(f"                    .or({or_condition})")

                    complex_condition = "\n".join(condition_lines)
                    conditions_code.append(f"                .where('{char}', {complex_condition})")
                    processed_chars.add(char)

            else:
                # 处理普通字符
                matched_blocks = [k for k, v in self.auto_char_map.items() if v == char]
                if matched_blocks:
                    condition = f"Predicates.blocks(GetRegistries.getBlock('{matched_blocks[0]}'))"
                    conditions_code.append(f"                .where('{char}', {condition})")
                    processed_chars.add(char)

        # 添加.build()
        conditions_code.append("                .build();")

        # 保存条件文件
        conditions_output_file = self.output_dir / f"{CLASS_PREFIX}_WhereConditions.txt"
        conditions_output_file.write_text("\n".join(conditions_code), encoding="utf-8")
        print(f"生成.where()条件和.build()文件: {conditions_output_file}")

    def _build_complex_condition(self, char, config, indent=4):
        """修复链式条件缩进"""
        if isinstance(config, str):
            return config  # 直接返回字符串条件
        space = ' ' * indent
        condition_lines = [config['condition']]

        for item in config.get('chain', []):
            if isinstance(item, dict) and 'or' in item:
                for or_item in item['or']:
                    # 处理字符串或字典类型的条件项
                    or_condition = self._build_complex_condition(char, or_item, indent + 4)
                    condition_lines.append(f"{space}.or({or_condition})")
        return '\n'.join(condition_lines)


# ----------------------
# 执行入口
# ----------------------
if __name__ == "__main__":
    try:
        converter = SchematicConverter()
        print(f"正在解析结构文件: {INPUT_FILE}")
        converter.load_schematic(INPUT_FILE)

        print("生成层级数据...")
        layers_data = converter.generate_layers()  # 修复：避免与实例变量名冲突

        print("生成Java结构类...")
        converter.generate_java_code(layers_data)

        print("生成主模式类和条件文件...")
        converter.generate_pattern_code_snippet()

        print("生成完成！文件输出至: {}".format(
            Path(OUTPUT_ROOT) / STRUCTURE_DIR
        ))
    except Exception as e:
        print(f"转换失败: {str(e)}")