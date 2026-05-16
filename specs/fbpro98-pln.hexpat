// FBPro98 .pln — ImHex pattern converted from Hex Workshop .hsl
// Source: fbpro_pln.hsl
// Notes:
// - Hex Workshop had: #pragma byteorder(little_endian)
//   ImHex equivalent: #pragma endian little
// - Enum BLOCK_TYPE values in the .hsl were string literals ("G95:", etc.)
//   ImHex doesn't support enum string literals

#pragma endian little
#pragma pattern_limit 200000

#include <std/sys.pat>

// ---- 4-byte tags (little-endian) ----
enum BlockType : u32 {
    G95 = 0x3A353947,  // "G95:"
    J95 = 0x3A35394A,  // "J95:"
    S98 = 0x3A383953   // "S98:"
};

// ---- Stock/custom flag ----
enum StockFlag : u8 {
    NOT_STOCK = 0x00,
    STOCK     = 0x01
};

// ---- One play entry (variable-length if not stock) ----
struct PlayInPlan {
    StockFlag stockFlag;   // 0x00 not stock, 0x01 stock
    if (stockFlag != StockFlag::NOT_STOCK && stockFlag != StockFlag::STOCK)
        continue;
    u8        playCategory;
    u8        specialCategory;
    u8        userCategory;

    //std::assert(stockFlag == StockFlag::NOT_STOCK || stockFlag == StockFlag::STOCK, "Invalid stock flag");

    if (stockFlag == StockFlag::NOT_STOCK) {
        char playName[];
    } else {
        char  playName[8];
        u32   offset;      // Unknown offset (unrelated to the game plan file)
        u16   size;        // Unknown size (unrelated to the game plan file)
    }
};

// ---- G95: header + four ordered offset arrays + play data ----
struct G95 {
    BlockType id;   // "G95:"
    u32       len;  // data length (excludes id+len)

    u8  audible[4];       // 00|01|02|03 // Ignore for PNFL game plans
    u16 playOffsets[86];  // 64 Normal, 20 Special, 2 Clock
                          // Offset from 0x0C to the start of each play in the
                          // plan; Any empty slots have an offset of 0.
                          // Normal plays have specialCategory of 0.
                          // Special teams plays go in order of specialCategory,
                          // 1-10, alternating between non-stock and stock
                          // versions of each. Each special teams play has
                          // playCategory of 1 and userCategory of 1.

    // Plays continue until the end of the G95 block (id+len header is 8 bytes,
    // then `len` bytes of data).
    PlayInPlan plays[while($ < addressof(this) + 8 + len)];

    std::assert(id == BlockType::G95, "Invalid block ID");
};

// ---- J95: header + 7-byte data (length = 0x07) ----
enum ProfileType : u8 { DEFENSE = 0, OFFENSE = 1 };

struct J95 {
    BlockType   id;   // "J95:"
    u32         len;  // data length (excludes id+len)

    // data (1 + 2 + 2 + 2 = 7 bytes)
    ProfileType profileType;    // 0=DEFENSE, 1=OFFENSE
    u16         numCustomPlays;
    u16         numStockPlays;
    u16         numSpecialPlays;

    std::assert(id == BlockType::J95, "Invalid block ID");
    std::assert(len == 7, "Invalid data length");
};

// ---- S98: header + length-prefixed filename (last block) ----
struct S98 {
    BlockType id;   // "S98:"
    u32       len;  // data length (excludes id+len)

    char      map_filename[len];  // STOCK98.MAP (null-terminated)
    // ignore any trailing padding at EOF

    std::assert(id == BlockType::S98, "Invalid block ID");
    std::assert(len == 12, "Invalid data length");
};

// ---- Top-level file ----
struct PlnFile {
    G95 g95;    // 0x00
    J95 j95;    // 0x04
    S98 s98;    // 0x08
};


PlnFile plnfile_at_0x00 @ 0x00;
