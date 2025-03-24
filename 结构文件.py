import re
import string
from pathlib import Path
from itertools import product

# ----------------------
# 配置区
# ----------------------
INPUT_FILE = "物质解压器.txt"
OUTPUT_ROOT = "multiblock"  # 固定第一层目录
PACKAGE_NAME = "org.qiuyeqaq.gtl_extend.common.multiblock.structure.BlackHoleMatterDecompressor"
LAYERS_PER_FILE = 20
CLASS_PREFIX = "BlackHoleMatterDecompressor"
BASE_STRUCTURE = "FactoryAPI.shape()"

# 从输入文件名获取结构名称
STRUCTURE_DIR = Path(INPUT_FILE).stem

SPECIAL_CHARS = {
    '~': {
        'condition': "Predicates.controller(definition.getBlock('{}'))",
        'keywords': [# 新增通用识别关键词
            'gtl_extend:black_hole_matter_decompressor'
        ]
    }
}
COMPLEX_CONDITIONS = {
    "A": {
        "condition": "Predicates.blocks(GetRegistries.getBlock('{}'))",  # 可配置的模板
        "keywords": ["gtceu:high_power_casing"],  # 匹配关键词
        "chain": [
            ".setMinGlobalLimited(10)",
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
        self.length = 0
        self.height = 0
        self.auto_char_map = {}
        self.used_chars = set(SPECIAL_CHARS.keys())
        self.char_generator = self.create_char_generator()
        self.layers = []  # 显式初始化实例变量

    def create_char_generator(self):
        """字符生成序列（跳过已使用字符）"""
        # 单字母序列
        for c in string.ascii_uppercase:
            if c not in self.used_chars:
                yield c
        # 双字母组合
        for first, second in product(string.ascii_uppercase, repeat=2):
            combo = f"{first}{second}"
            if combo not in self.used_chars:
                yield combo

    def load_schematic(self, file_path):
        """加载并解析结构文件"""
        content = Path(file_path).read_text(encoding="utf-8")

        # 解析尺寸
        self.length = int(re.search(r"Length: (\d+)S", content).group(1))
        self.height = int(re.search(r"Height: (\d+)S", content).group(1))

        # 解析调色板
        self.parse_palette(content)

        # 解析块数据
        self.decode_block_data(content)

        # 数据校验
        expected_size = self.length ** 2 * self.height
        if len(self.block_data) != expected_size:
            raise ValueError(f"数据长度不匹配！预期: {expected_size}, 实际: {len(self.block_data)}")

    def parse_palette(self, content):
        """解析调色板并生成字符映射（完整修复版）"""
        palette_section = re.search(r"Palette: {([^}]+)}", content, re.DOTALL)
        if not palette_section:
            raise ValueError("无法找到Palette定义")

        # 使用迭代器直接提取键值对
        entries = []
        pattern = re.compile(r'"\s*(.*?)\s*"\s*:\s*(\d+)')  # 允许键值周围的空格
        for match in pattern.finditer(palette_section.group(1)):
            block_name = match.group(1).replace('\\"', '"')  # 处理转义引号
            block_id = int(match.group(2))
            entries.append((block_name, block_id))

        # 处理特殊方块
        for block_name, block_id in entries:
            # 空气方块处理
            if block_name == "minecraft:air":
                self._handle_air_block(block_id)
                continue

            # 特殊字符匹配（基于配置的关键词）
            matched_special = False
            for char, config in SPECIAL_CHARS.items():
                keywords = config.get('keywords', [])
                for keyword in keywords:
                    if keyword.lower() in block_name.lower():
                        self.palette[block_id] = char
                        self.auto_char_map[block_name] = char
                        self.used_chars.add(char)
                        print(f"识别到特殊方块 {block_name} -> {char} (关键词: {keyword})")
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
                        self.palette[block_id] = char
                        self.auto_char_map[block_name] = char
                        self.used_chars.add(char)
                        print(f"识别到复杂条件方块 {block_name} -> {char} (关键词: {keyword})")
                        matched_complex = True
                        break
                if matched_complex:
                    break
            if matched_complex:
                continue

            # 自动分配字符（增强版）
            if block_name not in self.auto_char_map:
                try:
                    new_char = next(self.char_generator)
                    while new_char in self.used_chars:
                        new_char = next(self.char_generator)
                    self.auto_char_map[block_name] = new_char
                    self.used_chars.add(new_char)
                except StopIteration:
                    raise ValueError("字符资源耗尽，请减少唯一方块种类")

            # 更新palette映射
            assigned_char = self.auto_char_map[block_name]
            self.palette[block_id] = assigned_char
            print(f"映射 {block_name} (ID:{block_id}) -> {assigned_char}")

    def _handle_air_block(self, block_id):
        """特殊处理空气方块"""
        self.palette[int(block_id)] = ' '
        self.auto_char_map["minecraft:air"] = ' '
        self.used_chars.add(' ')

    def decode_block_data(self, content):
        """解析方块数据（添加校验）"""
        match = re.search(r"BlockData: bytes\(([^)]+)", content)
        if not match:
            raise ValueError("无法找到BlockData")

        byte_values = match.group(1).split(", ")
        self.block_data = []
        for b in byte_values:
            try:
                block_id = int(b)
                if block_id not in self.palette:
                    raise ValueError(f"发现未映射的方块ID: {block_id}")
                self.block_data.append(block_id)
            except ValueError:
                print(f"警告: 忽略无效的BlockData值: {b}")

    def generate_layers(self):
        """生成分层结构数据（带调试信息）"""
        self.layers = []
        for y in range(self.length):
            layer = []
            for z in range(self.height):
                row = []
                for x in range(self.length):
                    index = z * self.length ** 2 + y * self.length + x
                    block_id = self.block_data[index]
                    char = self.palette.get(block_id, '?')
                    if char == '?':
                        print(f"警告: 位置({x},{y},{z}) 发现未映射ID: {block_id}")
                    row.append(char)
                layer.append("".join(row))
            self.layers.append(layer)
        return self.layers  # 返回实例变量

    def generate_java_code(self, layers):
        """生成Java分层类文件"""
        total_files = (len(layers) + LAYERS_PER_FILE - 1) // LAYERS_PER_FILE

        for file_num in range(total_files):
            start = file_num * LAYERS_PER_FILE
            end = min((file_num + 1) * LAYERS_PER_FILE, len(layers))
            file_layers = layers[start:end]

            class_name = f"{CLASS_PREFIX}_Part{file_num + 1}"
            code = [
                f"package {PACKAGE_NAME};",  # 保持原始包名
                "",
                f"public class {class_name} {{",
                ""
            ]

            for i, layer in enumerate(file_layers, start + 1):
                code.append(f"    public static final String[] LAYER_{i:03} = {{")
                code.extend([f'        "{row}",' for row in layer])
                code.append("    };\n")

            code.append("}")

            # 写入到统一目录
            output_file = self.output_dir / f"{class_name}.java"
            output_file.write_text("\n".join(code), encoding="utf-8")
            print(f"生成结构类文件: {output_file}")

    def generate_pattern_code_snippet(self):
        """生成匹配条件代码"""
        unique_chars = set()
        for layer in self.layers:
            for row in layer:
                unique_chars.update(row)

        where_lines = []
        for char in sorted(unique_chars, key=lambda x: (x not in SPECIAL_CHARS, x)):
            # 处理特殊字符（如~）
            if char in SPECIAL_CHARS:
                config = SPECIAL_CHARS[char]
                # 填充占位符：将{}替换为第一个keyword
                filled_condition = config['condition'].format(config['keywords'][0])
                where_lines.append(f".where('{char}', {filled_condition})")

            # 处理复杂条件（如A）
            elif char in COMPLEX_CONDITIONS:
                config = COMPLEX_CONDITIONS[char]
                matched_blocks = [k for k, v in self.auto_char_map.items() if v == char]
                if matched_blocks:
                    # 填充占位符并构建条件链
                    base_condition = config['condition'].format(matched_blocks[0])
                    condition = self._build_complex_condition(char, {
                        "condition": base_condition,
                        "chain": config['chain']
                    })
                    where_lines.append(f".where('{char}', {condition})")
            print(f"警告: 复杂条件字符 '{char}' 未找到对应方块")

        # 确保使用 self.layers 生成 aisle
        pattern_code = [
            f"public static final MultiblockShape PATTERN = {BASE_STRUCTURE}",
            *["    .aisle(\"{}\")".format(row) for layer in self.layers for row in layer],
            "    .where(' ', Predicates.any())",  # 固定空格的where条件
            *["    " + line.rstrip() + " \\" for line in where_lines],  # 添加换行连接符
            "    .build();"
        ]

        output_file = self.output_dir / "PatternConditions.java"
        output_file.write_text("\n".join(pattern_code), encoding="utf-8")
        print(f"生成匹配条件: {output_file}")
        condition = SPECIAL_CHARS[char]['condition'].format(*SPECIAL_CHARS[char]['keywords'])

    def _build_complex_condition(self, char, config, indent=4):
        """构建复杂条件表达式"""
        space = ' ' * indent
        if isinstance(config, str):
            return config

        # 初始化基础条件
        condition_lines = [config['condition']]

        for item in config.get('chain', []):
            if isinstance(item, dict) and 'or' in item:
                # 处理OR条件
                or_conditions = [
                    self._build_complex_condition(char, or_item, indent + 8)
                    for or_item in item['or']
                ]
                or_block = ",\n".join([f"{' ' * (indent + 4)}{c}" for c in or_conditions])
                condition_lines.append(f".or(\n{' ' * (indent + 4)}{or_block}\n{space})")
            else:
                # 直接添加链式调用
                condition_lines.append(f"{item}")

        return " \\\n".join([
            f"{condition_lines[0]}",
            *[f"{space}{line}" for line in condition_lines[1:]]
        ])


# ----------------------
# 执行入口
# ----------------------
if __name__ == "__main__":
    try:
        converter = SchematicConverter()
        print(f"正在解析结构文件: {INPUT_FILE}")
        converter.load_schematic(INPUT_FILE)

        print("生成层级数据...")
        converter.generate_layers()  # 必须调用以初始化self.layers

        print("生成Java结构类...")
        converter.generate_java_code(converter.layers)

        print("生成匹配条件代码...")
        converter.generate_pattern_code_snippet()  # 移除参数

        print("生成完成！文件输出至: {}".format(
            Path(OUTPUT_ROOT) / STRUCTURE_DIR
        ))
    except Exception as e:
        print(f"转换失败: {str(e)}")