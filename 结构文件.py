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
        'keywords': ['gtceu:annihilate_generator[facing=south,server_tick=false,upwards_facing=north]']
    }
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
        """解析调色板并生成字符映射"""
        palette_section = re.search(r"Palette: {([^}]+)}", content, re.DOTALL)
        if not palette_section:
            raise ValueError("无法找到Palette定义")

        entries = re.findall(r'"([^"]+)": (\d+)\s*', palette_section.group(1))
        for block_name, block_id in entries:
            # 强制处理空气方块
            if block_name == "minecraft:air":
                self._handle_air_block(block_id)
                continue
            # 新增逻辑：优先匹配SPECIAL_CHARS的关键词
            matched_special = False
            for char, config in SPECIAL_CHARS.items():
                if any(keyword in block_name for keyword in config['keywords']):
                    self.palette[int(block_id)] = char
                    self.auto_char_map[block_name] = char
                    self.used_chars.add(char)
                    matched_special = True
                    break
            if matched_special:
                continue

            # 自动识别控制器（根据名称特征）
            if "controller" in block_name.lower() or "control_toroid" in block_name:
                self.palette[int(block_id)] = '~'
                self.auto_char_map[block_name] = '~'
                self.used_chars.add('~')
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
        """生成分层结构数据（调整后的顺序）"""
        self.layers = []  # 初始化实例变量
        for y in range(self.length):
            layer = []
            for z in range(self.height):
                row = []
                for x in range(self.length):
                    index = z * self.length ** 2 + y * self.length + x
                    block_id = self.block_data[index]
                    row.append(self.palette.get(block_id, '?'))
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
        for layer in self.layers:  # 使用实例变量
            for row in layer:
                unique_chars.update(row)

        where_lines = []
        for char in sorted(unique_chars, key=lambda x: (x not in SPECIAL_CHARS, x)):
            if char in SPECIAL_CHARS:
                # 修正为正确的条件引用格式
                where_lines.append(f".where('{char}', {SPECIAL_CHARS[char]['condition']})")
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
                where_lines.append(f".where('{char}', {conditions})")
            else:
                print(f"警告: 字符 '{char}' 未找到对应方块定义")

        # 确保使用 self.layers 生成 aisle
        pattern_code = [
            f"public static final MultiblockShape PATTERN = {BASE_STRUCTURE}",
            *["    .aisle(\"{}\")".format(row) for layer in self.layers for row in layer],
            "    .where(' ', Predicates.any())",
            *["    " + line for line in where_lines],
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