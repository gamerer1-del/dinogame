# Blender で部屋の見た目を作るスクリプト

`docs/blender-guide.md` の寸法どおりに、部屋のモデルとテクスチャを Python で組み立てて
`assets/models/rooms/<部屋>.glb` に書き出します。テクスチャも numpy で作るので、素材のダウンロードは要りません。

| ファイル | 中身 |
| --- | --- |
| `common.py` | 箱・壁・板・配管の部品、ワールド座標の UV、マテリアル、glb 書き出し |
| `textures.py` | 金属パネル、コンクリート、床、水たまり、書類、爪痕、割れた画面、警告ストライプ |
| `observation.py` | 観察室 |

## 作り直し方

Blender の「Scripting」タブ（または Blender MCP）で次を実行します。

```python
import sys, importlib
sys.path.insert(0, r"<リポジトリの場所>\tools\blender")
import common, textures, observation
for m in (common, textures, observation):
    importlib.reload(m)
observation.build()    # コレクション Room_observation に組み立てる
observation.export()   # assets/models/rooms/observation.glb に書き出す
```

書き出したら Godot でプロジェクトを開き直すと、その部屋の箱が隠れてモデルが表示されます。
`textures/` と `*.blend` は作業用なのでコミットしません。
