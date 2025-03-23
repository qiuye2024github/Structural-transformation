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
    '~': "Predicates.controller(blocks(definition.getBlock()))",
    ' ': "Predicates.any()"
}
COMPLEX_CONDITIONS = {
    "A": {
        "base": "Predicates.blocks(GetRegistries.getBlock('gtceu:high_temperature_smelting_casing'))",
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
        # 创建两级目录结构
        self.output_dir = Path(OUTPUT_ROOT) / STRUCTURE_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化其他成员变量
        self.palette = {}
        self.block_data = []
        self.length = 0
        self.height = 0
        self.auto_char_map = {}
        self.used_chars = set(SPECIAL_CHARS.keys())
        self.char_generator = self.create_char_generator()

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
        """解析调色板并生成字符映射"""
        palette_section = re.search(r"Palette: {([^}]+)}", content, re.DOTALL)
        if not palette_section:
            raise ValueError("无法找到Palette定义")

        entries = re.findall(r'"([^"]+)": (\d+)\s*', palette_section.group(1))
        for block_name, block_id in entries:
            # 处理空气方块
            if block_name == "minecraft:air":
                self._handle_air_block(block_id)
                continue

            # 已映射的方块跳过
            if block_name in self.auto_char_map:
                continue

            # 分配新字符
            try:
                assigned_char = next(self.char_generator)
                while assigned_char in self.used_chars:
                    assigned_char = next(self.char_generator)
            except StopIteration:
                raise ValueError("字符资源耗尽，无法分配更多唯一标识符")

            self.auto_char_map[block_name] = assigned_char
            self.palette[int(block_id)] = assigned_char
            self.used_chars.add(assigned_char)

    def _handle_air_block(self, block_id):
        """特殊处理空气方块"""
        self.palette[int(block_id)] = ' '
        self.auto_char_map["minecraft:air"] = ' '
        self.used_chars.add(' ')

    def decode_block_data(self, content):
        """解析方块数据"""
        match = re.search(r"BlockData: bytes\(([^)]+)", content)
        if not match:
            raise ValueError("无法找到BlockData")

        byte_values = match.group(1).split(", ")
        try:
            self.block_data = [int(b) for b in byte_values]
        except ValueError:
            raise ValueError("BlockData包含无效数字")

    def generate_layers(self):
        """生成分层结构数据"""
        layers = []
        for z in range(self.height):
            layer = []
            for y in range(self.length):
                row = []
                for x in range(self.length):
                    index = z * self.length**2 + y * self.length + x
                    block_id = self.block_data[index]
                    row.append(self.palette.get(block_id, '?'))
                layer.append("".join(row))
            layers.append(layer)
        return layers

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

    def generate_aisle_code_snippet(self, total_layers):
        """生成结构调用代码（精确格式）"""
        lines = [
            "// 结构调用代码片段 - 请粘贴到对应位置",
            f"{BASE_STRUCTURE}"
        ]

        current_part = 1
        part_layers = []

        for layer_num in range(1, total_layers + 1):
            # 计算当前属于哪个Part
            part_num = (layer_num - 1) // LAYERS_PER_FILE + 1

            # 当Part变化时添加换行
            if part_num != current_part:
                lines.append("")
                current_part = part_num

            class_name = f"{CLASS_PREFIX}_Part{part_num}"
            layer_id = f"LAYER_{layer_num:03}"
            lines.append(f"    .aisle({class_name}.{layer_id})")

        # 添加结尾分号
        lines[-1] += ";"

        output_file = self.output_dir / "StructureAisleCalls.java"
        output_file.write_text("\n".join(lines))
        print(f"生成调用代码: {output_file}")

    def generate_pattern_code_snippet(self, layers):
        """生成匹配条件代码"""
        unique_chars = set()
        for layer in layers:
            for row in layer:
                unique_chars.update(row)

        where_lines = []
        for char in sorted(unique_chars, key=lambda x: (x not in SPECIAL_CHARS, x)):
            if char in SPECIAL_CHARS:
                where_lines.append(f".where('{char}', {SPECIAL_CHARS[char]})")
                continue

            if char in COMPLEX_CONDITIONS:
                condition = self._build_complex_condition(char, COMPLEX_CONDITIONS[char])
                where_lines.append(f".where('{char}', {condition})")
                continue

            matched_blocks = [k for k, v in self.auto_char_map.items() if v == char]
            if matched_blocks:
                conditions = " | ".join(
                    [f"Predicates.blocks(GetRegistries.getBlock('{b}'))"
                     for b in matched_blocks]
                )
                if len(char) > 1:
                    conditions = f"Predicates.matches({conditions})"
                where_lines.append(f".where('{char}', {conditions})")
            else:
                print(f"警告: 字符 '{char}' 未找到对应方块定义")

        pattern_code = [
            f"public static final MultiblockShape PATTERN = {BASE_STRUCTURE}",
            *["    .aisle(\"{}\")".format(row) for layer in layers for row in layer],
            "    .where(' ', Predicates.any())",
            *["    " + line for line in where_lines],
            "    .build();"
        ]

        output_file = self.output_dir / "PatternConditions.java"
        output_file.write_text("\n".join(pattern_code))
        print(f"生成匹配条件: {output_file}")

    def _build_complex_condition(self, char, config, indent=4):
        """构建复杂条件表达式"""
        space = ' ' * indent
        if isinstance(config, str):
            return config

        condition_lines = [config['base']]
        for item in config.get('chain', []):
            if isinstance(item, dict) and 'or' in item:
                or_conditions = [
                    self._build_complex_condition(char, or_item, indent + 8)
                    for or_item in item['or']
                ]
                condition_lines.append(
                    f".or(\n{' ' * (indent + 4)}" +
                    f",\n{' ' * (indent + 4)}".join(or_conditions) +
                    f"\n{space})"
                )
            else:
                condition_lines.append(f"{item}")

        return '\n'.join([
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
        layers = converter.generate_layers()

        print("生成Java结构类...")
        converter.generate_java_code(layers)

        print("生成结构调用代码...")
        converter.generate_aisle_code_snippet(len(layers))

        print("生成匹配条件代码...")
        converter.generate_pattern_code_snippet(layers)

        print("生成完成！文件输出至: {}".format(
            Path(OUTPUT_ROOT) / STRUCTURE_DIR
        ))
    except Exception as e:
        print(f"转换失败: {str(e)}")